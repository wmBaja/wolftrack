import asyncio
import socket
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv

from config import AppConfig
from logging_config import setup_logging, get_logger

# Load env FIRST
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

from zmq_consumer import zmq_listener, zmq_context
from api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the ZMQ background listener
    task = None
    if config.zmq.enabled:
        task = asyncio.create_task(zmq_listener(config))
    yield
    # Stop cleanly
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    zmq_context.destroy(linger=0)

app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    host = config.fastapi.host
    port = config.fastapi.port
    
    if port == 0:
        # Dynamically bind to port 0 to get an ephemeral port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, 0))
        port = sock.getsockname()[1]
        sock.close() 
    
    # Print the port securely so Electron can parse it from stdout
    print(f"WOLFTRACK_WS_PORT={port}", flush=True)
    
    # Run uvicorn on the discovered port (we use error level to keep stdout clean)
    uvicorn.run(app, host=host, port=port, log_level="error")
