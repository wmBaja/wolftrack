import os
import shutil
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException, UploadFile, File, Form
from ws_manager import manager
from pipeline.manager import PipelineManager

router = APIRouter()

class ConfigUpdate(BaseModel):
    source: str
    log_file: Optional[str] = None
    dbc_file: Optional[str] = None
    playback_speed: Optional[float] = None


class LiveSourceConnectRequest(BaseModel):
    flask_host: str
    flask_port: int
    zmq_host: str
    zmq_port: int

@router.get("/api/config")
async def get_config(request: Request):
    pipeline_config = request.app.state.config.pipeline
    return {
        "source": pipeline_config.source,
        "log_file": pipeline_config.log_file,
        "dbc_file": pipeline_config.dbc_file,
        "playback_speed": getattr(pipeline_config, "playback_speed", 1.0)
    }


@router.get("/api/live_source")
async def get_live_source(request: Request):
    live_source = request.app.state.config.live_source
    return {
        "connected": live_source.connected,
        "flask_host": live_source.flask_host,
        "flask_port": live_source.flask_port,
        "zmq_host": live_source.zmq_host,
        "zmq_port": live_source.zmq_port,
    }

@router.get("/api/signals")
async def get_signals(request: Request):
    pm = getattr(request.app.state, 'pipeline_manager', None)
    if not pm or not getattr(pm, 'source', None) or not getattr(pm.source, 'db', None):
        return {"signals": []}
    
    signals = []
    for msg in pm.source.db.messages:
        for sig in msg.signals:
            signals.append({
                "id": f"{msg.name}.{sig.name}",
                "message": msg.name,
                "name": sig.name,
                "unit": sig.unit
            })
    return {"signals": signals}

@router.post("/api/upload_config")
async def upload_config(
    request: Request,
    source: str = Form(...),
    playback_speed: float = Form(1.0),
    log_file_upload: Optional[UploadFile] = File(None),
    dbc_file_upload: Optional[UploadFile] = File(None),
    existing_log: Optional[str] = Form(None),
    existing_dbc: Optional[str] = Form(None)
):
    if source not in ["zmq", "logfile"]:
        raise HTTPException(status_code=400, detail="Source must be 'zmq' or 'logfile'.")
        
    # Use a writable directory provided by the environment (e.g. Electron's userData path)
    base_dir = os.environ.get("WOLFTRACK_USER_DATA", os.getcwd())
    upload_dir = os.path.join(base_dir, "logs", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    dbc_upload_dir = os.path.join(base_dir, "dbc")
    os.makedirs(dbc_upload_dir, exist_ok=True)
    
    config = request.app.state.config
    config.pipeline.source = source
    config.pipeline.playback_speed = playback_speed
    
    if source == "logfile":
        if log_file_upload and log_file_upload.filename:
            # Clear old logs
            for f in os.listdir(upload_dir):
                try:
                    os.remove(os.path.join(upload_dir, f))
                except Exception:
                    pass
            
            file_path = os.path.join(upload_dir, log_file_upload.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(log_file_upload.file, buffer)
            config.pipeline.log_file = file_path
        elif existing_log:
            if os.path.isabs(existing_log) and os.path.exists(existing_log):
                config.pipeline.log_file = existing_log
            else:
                config.pipeline.log_file = os.path.join(upload_dir, os.path.basename(existing_log))
        else:
            raise HTTPException(status_code=400, detail="Log file is required for logfile source.")
            
    if dbc_file_upload and dbc_file_upload.filename:
        # Clear old dbcs
        for f in os.listdir(dbc_upload_dir):
            try:
                os.remove(os.path.join(dbc_upload_dir, f))
            except Exception:
                pass
                
        dbc_path = os.path.join(dbc_upload_dir, dbc_file_upload.filename)
        with open(dbc_path, "wb") as buffer:
            shutil.copyfileobj(dbc_file_upload.file, buffer)
        config.pipeline.dbc_file = dbc_path
    elif existing_dbc:
        if os.path.isabs(existing_dbc) and os.path.exists(existing_dbc):
            config.pipeline.dbc_file = existing_dbc
        else:
            config.pipeline.dbc_file = os.path.join(dbc_upload_dir, os.path.basename(existing_dbc))
        
    # Reinitialize pipeline manager
    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        
    request.app.state.pipeline_manager = PipelineManager(config)
    if request.app.state.pipeline_manager.has_source():
        await request.app.state.pipeline_manager.start()
    return {"status": "success", "message": "Pipeline configuration uploaded and restarted successfully"}


@router.post("/api/live_source/connect")
async def connect_live_source(request: Request, payload: LiveSourceConnectRequest):
    config = request.app.state.config
    config.pipeline.source = "zmq"
    config.live_source.flask_host = payload.flask_host
    config.live_source.flask_port = payload.flask_port
    config.live_source.zmq_host = payload.zmq_host
    config.live_source.zmq_port = payload.zmq_port
    config.live_source.connected = True

    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()

    request.app.state.pipeline_manager = PipelineManager(config)
    await request.app.state.pipeline_manager.start()
    await manager.broadcast_json({
        "type": "live_source",
        "connected": True,
        "flask_host": config.live_source.flask_host,
        "flask_port": config.live_source.flask_port,
        "zmq_host": config.live_source.zmq_host,
        "zmq_port": config.live_source.zmq_port,
    })
    return {"status": "success", "message": "Live source connected successfully"}


@router.post("/api/live_source/disconnect")
async def disconnect_live_source(request: Request):
    config = request.app.state.config

    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        request.app.state.pipeline_manager = None

    config.live_source.connected = False
    await manager.broadcast_json({
        "type": "live_source",
        "connected": False,
        "flask_host": config.live_source.flask_host,
        "flask_port": config.live_source.flask_port,
        "zmq_host": config.live_source.zmq_host,
        "zmq_port": config.live_source.zmq_port,
    })
    return {"status": "success", "message": "Live source disconnected successfully"}

@router.post("/api/stop")
async def stop_pipeline(request: Request):
    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        # Nullify the active pipeline manager
        request.app.state.pipeline_manager = None
        request.app.state.config.live_source.connected = False
        return {"status": "success", "message": "Pipeline stopped successfully"}
    return {"status": "success", "message": "Pipeline is already stopped"}

@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the socket open until client drops or sends close frame
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
