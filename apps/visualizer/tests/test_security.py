from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from api.config import router as config_router
from src.security import BackendSecurityMiddleware


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
