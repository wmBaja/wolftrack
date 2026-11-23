from fastapi import WebSocket
from logging_config import get_logger

logger = get_logger(__name__)

class ConnectionManager:
    def __init__(self):
        self.connections: dict[WebSocket, dict] = {}

    @property
    def active_connections(self):
        return set(self.connections)

    @property
    def subscribed_signals(self) -> set[str]:
        return set().union(*(state['signals'] for state in self.connections.values())) if self.connections else set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections[websocket] = {'signals': set(), 'live_window_seconds': 15.0}

    def subscribe(self, websocket: WebSocket, signals: list[str], live_window_seconds: float):
        state = self.connections.get(websocket)
        if state is not None:
            state['signals'] = {str(signal) for signal in signals}
            state['live_window_seconds'] = float(live_window_seconds)

    def disconnect(self, websocket: WebSocket):
        self.connections.pop(websocket, None)
        logger.info("Client disconnected")

    async def broadcast_json(self, message: dict):
        disconnected = set()
        for connection, state in tuple(self.connections.items()):
            client_message = message
            if message.get('type') == 'live_batch':
                signals = {key: value for key, value in message.get('signals', {}).items() if key in state['signals']}
                if not signals and not message.get('dropped_batches'):
                    continue
                client_message = {**message, 'signals': signals}
            try:
                await connection.send_json(client_message)
            except RuntimeError:
                disconnected.add(connection)
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()
