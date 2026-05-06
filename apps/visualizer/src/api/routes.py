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

@router.get("/api/config")
async def get_config(request: Request):
    pipeline_config = request.app.state.config.pipeline
    return {
        "source": pipeline_config.source,
        "log_file": pipeline_config.log_file,
        "dbc_file": pipeline_config.dbc_file,
        "playback_speed": getattr(pipeline_config, "playback_speed", 1.0)
    }

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
        
    # Reinitialize pipeline manager
    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        
    request.app.state.pipeline_manager = PipelineManager(config, request.app.state.dbc_manager)
    await request.app.state.pipeline_manager.start()
    return {"status": "success", "message": "Pipeline configuration uploaded and restarted successfully"}

@router.post("/api/stop")
async def stop_pipeline(request: Request):
    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        # Nullify the active pipeline manager
        request.app.state.pipeline_manager = None
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
