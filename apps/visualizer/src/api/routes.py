import os
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException
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

@router.post("/api/config")
async def update_config(update: ConfigUpdate, request: Request):
    if update.source not in ["zmq", "logfile"]:
        raise HTTPException(status_code=400, detail="Source must be 'zmq' or 'logfile'.")
        
    if update.log_file and not os.path.exists(update.log_file):
        raise HTTPException(status_code=400, detail=f"Log file not found: {update.log_file}")
        
    if update.dbc_file and not os.path.exists(update.dbc_file):
        raise HTTPException(status_code=400, detail=f"DBC file not found: {update.dbc_file}")
        
    # Update global config state
    config = request.app.state.config
    config.pipeline.source = update.source
    if update.log_file is not None:
        config.pipeline.log_file = update.log_file
    if update.dbc_file is not None:
        config.pipeline.dbc_file = update.dbc_file
    if getattr(update, 'playback_speed', None) is not None:
        config.pipeline.playback_speed = update.playback_speed
        
    # Reinitialize pipeline manager
    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        
    request.app.state.pipeline_manager = PipelineManager(config)
    await request.app.state.pipeline_manager.start()
    return {"status": "success", "message": "Pipeline configuration updated and restarted successfully"}

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
