from fastapi import APIRouter
from .common import *

router = APIRouter()

@router.get("/api/live_source")
async def get_live_source(request: Request):
    return serialize_live_source(request.app.state.config)

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

@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
                if data.get("type") == "subscribe":
                    manager.subscribe(websocket, data.get("signals", []), data.get("live_window_seconds", 15.0))
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        manager.disconnect(websocket)
