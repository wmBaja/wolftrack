from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import api.routes as routes
from config import AppConfig


class DummyPipelineManager:
    def __init__(self):
        self.stop_calls = 0

    async def stop(self):
        self.stop_calls += 1


def build_client():
    app = FastAPI()
    app.include_router(routes.router)
    app.state.config = AppConfig()
    app.state.pipeline_manager = DummyPipelineManager()
    broadcasts = []

    async def fake_broadcast(payload):
        broadcasts.append(payload)

    routes.manager.broadcast_json = fake_broadcast
    return TestClient(app), app, broadcasts


def test_stop_live_source_preserves_remembered_endpoint():
    client, app, broadcasts = build_client()
    app.state.config.live_source.flask_host = "daq.local"
    app.state.config.live_source.flask_port = 5000
    app.state.config.live_source.zmq_host = "daq.local"
    app.state.config.live_source.zmq_port = 5555
    app.state.config.live_source.connected = True

    response = client.post("/api/live_source/stop")

    assert response.status_code == 200
    assert app.state.pipeline_manager is None
    assert app.state.config.live_source.connected is False
    assert app.state.config.live_source.flask_host == "daq.local"
    assert app.state.config.live_source.zmq_host == "daq.local"
    assert broadcasts == [{
        "type": "live_source",
        "connected": False,
        "flask_host": "daq.local",
        "flask_port": 5000,
        "zmq_host": "daq.local",
        "zmq_port": 5555,
    }]


def test_disconnect_live_source_clears_remembered_endpoint():
    client, app, broadcasts = build_client()
    app.state.config.live_source.flask_host = "daq.local"
    app.state.config.live_source.flask_port = 5000
    app.state.config.live_source.zmq_host = "daq.local"
    app.state.config.live_source.zmq_port = 5555
    app.state.config.live_source.connected = True

    response = client.post("/api/live_source/disconnect")

    assert response.status_code == 200
    assert app.state.pipeline_manager is None
    assert app.state.config.live_source.connected is False
    assert app.state.config.live_source.flask_host is None
    assert app.state.config.live_source.flask_port is None
    assert app.state.config.live_source.zmq_host is None
    assert app.state.config.live_source.zmq_port is None
    assert broadcasts == [{
        "type": "live_source",
        "connected": False,
        "flask_host": None,
        "flask_port": None,
        "zmq_host": None,
        "zmq_port": None,
    }]
