import asyncio
import warnings
import os
import sys

if sys.platform == 'win32':
    warnings.filterwarnings("ignore", message="Proactor event loop does not implement add_reader.*", category=RuntimeWarning)
import socket
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

from config import AppConfig
from logging_config import setup_logging, get_logger

load_dotenv()
config = AppConfig.from_env()

_sys_logger = setup_logging(
    log_dir=config.appLog.log_dir,
    log_level=config.appLog.log_level,
    console_output=config.appLog.log_to_console,
    log_to_file=config.appLog.log_to_file,
    max_file_size_mb=config.appLog.max_log_file_size_mb,
    backup_count=config.appLog.log_backup_count,
    format_style=config.appLog.log_format
)

logger = get_logger(__name__)

from pipeline.manager import PipelineManager
from pipeline.log_query import log_query_service
from api.routes import router
from api.wts_routes import wts_router
from dbc_manager import DBCManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = config
    
    # Initialize global DBC manager
    user_data_dir = os.environ.get("WOLFTRACK_USER_DATA", os.getcwd())
    app.state.dbc_manager = DBCManager(user_data_dir)

    # WTS: the log index must use the real user-data cache dir even when the
    # singleton was created before the environment was set, and virtual
    # signals come from the active setup file.
    log_query_service.set_cache_dir(os.path.join(user_data_dir, "logs", "cache"))

    def wts_definitions_provider():
        dbc_manager = app.state.dbc_manager
        return dbc_manager.get_virtual_signals(), dbc_manager.get_definition_hashes()

    log_query_service.set_definitions_provider(wts_definitions_provider)

    def on_wts_changed(changed_ids):
        # File-level changes (select/upload/delete/rename) re-index the log
        # from the routes; signal edits recompute derived rows only.
        if changed_ids is not None:
            log_query_service.request_wts_recompute(changed_ids)

    app.state.dbc_manager.set_changed_callback(on_wts_changed)

    app.state.pipeline_manager = PipelineManager(app.state.config, app.state.dbc_manager)
    
    if app.state.pipeline_manager.has_source():
        await app.state.pipeline_manager.start()
    
    yield
    
    # Stop cleanly
    log_query_service.stop()
    if getattr(app.state, 'pipeline_manager', None):
        await app.state.pipeline_manager.stop()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(wts_router)

if __name__ == "__main__":
    host = config.fastapi.host
    port = config.fastapi.port
    
    if port == 0:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, 0))
        port = sock.getsockname()[1]
        sock.close() 
    
    print(f"WOLFTRACK_WS_PORT={port}", flush=True)
    
    uvicorn.run(app, host=host, port=port, log_level="error")
