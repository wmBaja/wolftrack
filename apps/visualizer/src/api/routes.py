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
        
    upload_dir = os.path.join(os.getcwd(), "logs", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    config = request.app.state.config
    config.pipeline.source = source
    config.pipeline.playback_speed = playback_speed
    
    if source == "logfile":
        if log_file_upload and log_file_upload.filename:
            file_path = os.path.join(upload_dir, log_file_upload.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(log_file_upload.file, buffer)
            config.pipeline.log_file = file_path
        elif existing_log:
            config.pipeline.log_file = existing_log
        else:
            raise HTTPException(status_code=400, detail="Log file is required for logfile source.")
            
    if dbc_file_upload and dbc_file_upload.filename:
        dbc_path = os.path.join(upload_dir, dbc_file_upload.filename)
        with open(dbc_path, "wb") as buffer:
            shutil.copyfileobj(dbc_file_upload.file, buffer)
        config.pipeline.dbc_file = dbc_path
    elif existing_dbc:
        config.pipeline.dbc_file = existing_dbc
        
    # Reinitialize pipeline manager
    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        
    request.app.state.pipeline_manager = PipelineManager(config)
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
