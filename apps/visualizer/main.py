import sys
import asyncio
import socket
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import zmq
import zmq.asyncio
import cantools
from pathlib import Path

# Global set for active websocket clients
active_connections = set()

# Use asyncio Context for ZMQ
zmq_context = zmq.asyncio.Context()

# Load a DBC file if available (Client-side decoding)
db = None
try:
    dbc_cache = list(Path('.').glob('*.dbc'))
    if dbc_cache:
        db = cantools.database.load_file(dbc_cache[0])
        print(f"Loaded DBC for client-side decoding: {dbc_cache[0].name}", file=sys.stderr)
except Exception as e:
    print(f"No DBC loaded: {e}", file=sys.stderr)

async def zmq_listener():
    """Background task to listen to the Logger DAQ ZMQ stream."""
    sock = zmq_context.socket(zmq.SUB)
    # Configure the DAQ ip here. Defaulting to localhost.
    sock.connect("tcp://127.0.0.1:5555")
    sock.setsockopt_string(zmq.SUBSCRIBE, "")
    
    print("Started ZMQ Subscriber checking tcp://127.0.0.1:5555...", file=sys.stderr)
    
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
            
            # Forward the frame (raw and decoded) to all active WebSocket clients
            disconnected = set()
            print(message)
            for ws in active_connections:
                try:
                    await ws.send_json(message)
                except RuntimeError:
                    # Connection dropped while iterating
                    disconnected.add(ws)

            # Cleanup dropped clients
            active_connections.difference_update(disconnected)
                
        except asyncio.CancelledError:
            print("ZMQ Thread shutting down.", file=sys.stderr)
            break
        except Exception as e:
            print(f"ZMQ Error: {e}", file=sys.stderr)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the ZMQ background listener
    task = asyncio.create_task(zmq_listener())
    yield
    # Stop cleanly
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    zmq_context.term()

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            # Keep the socket open until client drops or sends close frame
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print("Client disconnected", file=sys.stderr)

if __name__ == "__main__":
    # Dynamically bind to port 0 to get an ephemeral port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close() 
    
    # Print the port securely so Electron can parse it from stdout
    print(f"WOLFTRACK_WS_PORT={port}", flush=True)
    
    # Run uvicorn on the discovered port (we use error level to keep stdout clean)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
