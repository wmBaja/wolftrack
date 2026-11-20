import asyncio
import websockets
import json
import sys

async def test_stream(port):
    uri = f"ws://127.0.0.1:{port}/ws/stream"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Listening for data...")
            i = 0
            while True:
                data = await websocket.recv()
                parsed = json.loads(data)
                print(f"Frame {i}: {parsed}")
                i += 1
    except Exception as e:
        print(f"Failed to connect or read: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_client.py <port>")
        sys.exit(1)
    port = int(sys.argv[1])
    asyncio.run(test_stream(port))
