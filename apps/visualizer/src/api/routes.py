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


def serialize_live_source(config):
    live_source = config.live_source
    return {
        "connected": live_source.connected,
        "flask_host": live_source.flask_host,
        "flask_port": live_source.flask_port,
        "zmq_host": live_source.zmq_host,
        "zmq_port": live_source.zmq_port,
    }


def serialize_live_source_event(config):
    return {
        "type": "live_source",
        **serialize_live_source(config),
    }

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
    return serialize_live_source(request.app.state.config)

@router.get("/api/signals")
async def get_signals(request: Request):
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if not dbc_manager:
        return {"signals": []}
    
    return {"signals": dbc_manager.get_signals()}

@router.get("/api/dbc")
async def get_dbc_info(request: Request):
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if not dbc_manager:
        return {"available": [], "active": None}
    
    return {
        "available": dbc_manager.get_available_dbcs(),
        "active": dbc_manager.active_dbc_filename
    }

@router.post("/api/dbc/upload")
async def upload_dbc_route(
    request: Request,
    file: UploadFile = File(...)
):
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if not dbc_manager:
        raise HTTPException(status_code=500, detail="DBC Manager not initialized")
        
    if not file.filename.endswith('.dbc'):
        raise HTTPException(status_code=400, detail="File must be a .dbc file")
        
    content = await file.read()
    dbc_manager.upload_dbc(file.filename, content)
    
    pipeline_manager = getattr(request.app.state, 'pipeline_manager', None)
    if pipeline_manager and pipeline_manager.source:
        pipeline_manager.source.db = dbc_manager.get_active_dbc()
    
    return {"status": "success", "message": f"DBC {file.filename} uploaded successfully"}

@router.post("/api/dbc/select")
async def select_dbc_route(
    request: Request,
    filename: str = Form(...)
):
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if not dbc_manager:
        raise HTTPException(status_code=500, detail="DBC Manager not initialized")
        
    success = dbc_manager.select_dbc(filename)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to select DBC {filename}")
        
    pipeline_manager = getattr(request.app.state, 'pipeline_manager', None)
    if pipeline_manager and pipeline_manager.source:
        pipeline_manager.source.db = dbc_manager.get_active_dbc()
        
    return {"status": "success", "message": f"DBC {filename} selected"}

@router.delete("/api/dbc/{filename}")
async def delete_dbc_route(
    request: Request,
    filename: str
):
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if not dbc_manager:
        raise HTTPException(status_code=500, detail="DBC Manager not initialized")
        
    success = dbc_manager.delete_dbc(filename)
    if not success:
        raise HTTPException(status_code=404, detail=f"DBC {filename} not found")
        
    pipeline_manager = getattr(request.app.state, 'pipeline_manager', None)
    if pipeline_manager and pipeline_manager.source:
        pipeline_manager.source.db = dbc_manager.get_active_dbc()
        
    return {"status": "success", "message": f"DBC {filename} deleted"}

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
            
    # DBC file is now handled by DBCManager, so we just use the active one.
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if dbc_manager and dbc_manager.active_dbc_filename:
        # The pipeline manager will pull the DBC from the DBCManager, 
        # but we can set it in the config just in case.
        config.pipeline.dbc_file = os.path.join(base_dir, "dbc", dbc_manager.active_dbc_filename)
    else:
        config.pipeline.dbc_file = None
        
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)

    # Reinitialize pipeline manager
    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        
    request.app.state.pipeline_manager = PipelineManager(config, dbc_manager)
    if request.app.state.pipeline_manager.has_source():
        await request.app.state.pipeline_manager.start()
    return {"status": "success", "message": "Pipeline configuration uploaded and restarted successfully"}


@router.post("/api/live_source/connect")
async def connect_live_source(request: Request, payload: LiveSourceConnectRequest):
    config = request.app.state.config
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    config.pipeline.source = "zmq"
    config.live_source.flask_host = payload.flask_host
    config.live_source.flask_port = payload.flask_port
    config.live_source.zmq_host = payload.zmq_host
    config.live_source.zmq_port = payload.zmq_port
    config.live_source.connected = True

    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()

    request.app.state.pipeline_manager = PipelineManager(config, dbc_manager)
    await request.app.state.pipeline_manager.start()
    await manager.broadcast_json(serialize_live_source_event(config))
    return {"status": "success", "message": "Live source connected successfully"}


@router.post("/api/live_source/stop")
async def stop_live_source(request: Request):
    config = request.app.state.config

    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        request.app.state.pipeline_manager = None

    config.live_source.connected = False
    await manager.broadcast_json(serialize_live_source_event(config))
    return {"status": "success", "message": "Live source stopped successfully"}


@router.post("/api/live_source/disconnect")
async def disconnect_live_source(request: Request):
    config = request.app.state.config

    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        request.app.state.pipeline_manager = None

    config.live_source.connected = False
    config.live_source.flask_host = None
    config.live_source.flask_port = None
    config.live_source.zmq_host = None
    config.live_source.zmq_port = None
    await manager.broadcast_json(serialize_live_source_event(config))
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
