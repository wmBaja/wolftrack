from pathlib import Path
import sys

from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
import pytest
from starlette.websockets import WebSocketDisconnect

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from api.config import router as config_router
from src.security import ALLOWED_ORIGINS, BackendSecurityMiddleware


def test_api_requires_bearer_token_and_rejects_wrong_host():
    app = FastAPI()
    app.add_middleware(BackendSecurityMiddleware, token="test-token")

    app.include_router(config_router)

    client = TestClient(app)
    loopback = {"Host": "127.0.0.1"}
    assert client.get("/api/version", headers=loopback).status_code == 401
    response = client.get("/api/version", headers={**loopback, "Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert response.json() == {"version": "1.1.2", "visualizerApi": "1.0.0"}
    assert client.get("/api/version", headers={"Authorization": "Bearer test-token", "Host": "example.com"}).status_code == 403


def websocket_test_client():
    app = FastAPI()
    app.add_middleware(BackendSecurityMiddleware, token="test-token")

    @app.websocket("/ws/stream")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("connected")

    return TestClient(app)


def test_websocket_requires_token_and_accepts_allowed_origins():
    client = websocket_test_client()
    headers = {"Host": "127.0.0.1", "Origin": "null"}

    with pytest.raises(WebSocketDisconnect) as missing_token:
        with client.websocket_connect("/ws/stream", headers=headers):
            pass
    assert missing_token.value.code == 4401

    with client.websocket_connect("/ws/stream?token=test-token", headers=headers) as websocket:
        assert websocket.receive_text() == "connected"

    assert {"null", "file://", "http://localhost:3000", "http://127.0.0.1:3000"} <= ALLOWED_ORIGINS


def test_websocket_rejects_untrusted_origin():
    client = websocket_test_client()

    with pytest.raises(WebSocketDisconnect) as rejected:
        with client.websocket_connect(
            "/ws/stream?token=test-token",
            headers={"Host": "127.0.0.1", "Origin": "https://untrusted.example"},
        ):
            pass

    assert rejected.value.code == 4403
