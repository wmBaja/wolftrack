from fastapi import APIRouter
from .common import *

router = APIRouter()

@router.get("/api/version")
async def get_version():
    # Breaking changes to the plugin-facing backend contract bump the API major.
    return {"version": "1.1.2", "visualizerApi": "1.0.0"}

@router.get("/api/config")
async def get_config(request: Request):
    pipeline_config = request.app.state.config.pipeline
    return {
        "source": pipeline_config.source,
        "log_file": pipeline_config.log_file,
        "dbc_file": pipeline_config.dbc_file,
        "playback_speed": getattr(pipeline_config, "playback_speed", 0.0)
    }

@router.post("/api/upload_config")
async def upload_config(
    request: Request,
    source: str = Form(...),
    playback_speed: float = Form(0.0),
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

    # Reinitialize pipeline manager. A logfile index is owned separately from
    # the playback pipeline, so it must be cancelled explicitly before a new
    # source configuration can replace it.
    log_query_service.stop()
    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()

    request.app.state.pipeline_manager = PipelineManager(config, dbc_manager)
    if source == "zmq" and request.app.state.pipeline_manager.has_source():
        await request.app.state.pipeline_manager.start()
    elif source == "logfile":
        dbc_manager = getattr(request.app.state, 'dbc_manager', None)
        active_dbc = dbc_manager.get_active_dbc() if dbc_manager else None
        if active_dbc and config.pipeline.log_file:
            log_query_service.start_indexing(config.pipeline.log_file, active_dbc)

    return {"status": "success", "message": "Pipeline configuration uploaded and restarted successfully"}

@router.post("/api/stop")
async def stop_pipeline(request: Request):
    # Log-file indexing runs in its own worker thread and is not controlled by
    # PipelineManager. Signal it even when no pipeline manager is active.
    log_query_service.stop()
    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        # Nullify the active pipeline manager
        request.app.state.pipeline_manager = None
        request.app.state.config.live_source.connected = False
        return {"status": "success", "message": "Pipeline stopped successfully"}
    return {"status": "success", "message": "Pipeline is already stopped"}
