import sys
import asyncio
import random
import socket
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI()

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Emit dummy DAQ data format for testing
            data = {
                "timestamp": asyncio.get_event_loop().time(),
                "rpm": random.uniform(800, 7000),
                "speed_mph": random.uniform(0, 120),
                "temperatures": {
                    "engine": random.uniform(80, 110),
                    "coolant": random.uniform(70, 95)
                }
            }
            await websocket.send_json(data)
            await asyncio.sleep(0.05) # 20 Hz update rate
    except WebSocketDisconnect:
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
