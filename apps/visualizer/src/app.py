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
from core.pipeline.manager import PipelineManager
from core.pipeline.log_query import log_query_service
from api.config import router as config_router
from api.live_source import router as live_source_router
from api.logfile import router as logfile_router
from api.dbc import router as dbc_router
from api.export import router as export_router
from core.dbc_manager import DBCManager
from security import ALLOWED_ORIGINS, BackendSecurityMiddleware, backend_token, is_loopback_host

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

if not is_loopback_host(config.fastapi.host) and os.environ.get("WOLFTRACK_ALLOW_REMOTE_BINDING") != "true":
    raise RuntimeError("FASTAPI_HOST must be a loopback address unless WOLFTRACK_ALLOW_REMOTE_BINDING=true")

AUTH_TOKEN = backend_token()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = config
    
    # Initialize global DBC manager
    user_data_dir = os.environ.get("WOLFTRACK_USER_DATA", os.getcwd())
    app.state.dbc_manager = DBCManager(user_data_dir)
    
    app.state.pipeline_manager = PipelineManager(app.state.config, app.state.dbc_manager)
    
    if app.state.pipeline_manager.has_source():
        await app.state.pipeline_manager.start()
    
    yield
    
    # Stop cleanly
    log_query_service.stop()
    if getattr(app.state, 'pipeline_manager', None):
        await app.state.pipeline_manager.stop()

app = FastAPI(lifespan=lifespan)
app.state.auth_token = AUTH_TOKEN
app.add_middleware(BackendSecurityMiddleware, token=AUTH_TOKEN)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for feature_router in (config_router, live_source_router, logfile_router, dbc_router, export_router):
    app.include_router(feature_router)

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
