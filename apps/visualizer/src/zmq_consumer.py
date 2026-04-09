import asyncio
import zmq
import zmq.asyncio
from config import AppConfig
from logging_config import get_logger
from ws_manager import manager
from dbc_loader import load_dbc

logger = get_logger(__name__)

# Use asyncio Context for ZMQ
zmq_context = zmq.asyncio.Context()
db = load_dbc()

async def zmq_listener(config: AppConfig):
    """Background task to listen to the Logger DAQ ZMQ stream."""
    sock = zmq_context.socket(zmq.SUB)
    
    try:
        # Configure the DAQ ip here
        zmq_url = f"tcp://{config.zmq.host}:{config.zmq.port}"
        sock.connect(zmq_url)
        sock.setsockopt_string(zmq.SUBSCRIBE, "")
        
        logger.info(f"Started ZMQ Subscriber checking {zmq_url}...")
        
        while True:
            try:
                # Receive raw payload from wolftrack-logger
                message = await sock.recv_json()
                
                # Decode data client-side if we have a DBC
                if db and "arbitration_id" in message and "data" in message:
                    try:
                        data_bytes = bytes(message["data"])
                        decoded = db.decode_message(message['arbitration_id'], data_bytes)
                        message['decoded'] = decoded
                    except KeyError:
                        pass # Message not in DBC
                
                logger.debug(str(message))
                
                # Forward the frame (raw and decoded) to all active WebSocket clients
                await manager.broadcast_json(message)
                    
            except asyncio.CancelledError:
                logger.info("ZMQ Thread shutting down.")
                break
            except Exception as e:
                logger.error(f"ZMQ Error: {e}", exc_info=True)
                break
    finally:
        sock.close(linger=0)
