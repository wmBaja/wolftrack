"""Contract tests for every WTS endpoint and the extended setup endpoints
(TestClient; I7: legacy-only behavior keeps working)."""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.routes as routes
from api.wts_routes import wts_router
from config import AppConfig
from dbc_manager import DBCManager
from tests.helpers.make_blf import SYNTHETIC_DBC


@pytest.fixture
def client(tmp_user_data):
    app = FastAPI()
    app.include_router(routes.router)
    app.include_router(wts_router)
    app.state.config = AppConfig()
    app.state.dbc_manager = DBCManager(str(tmp_user_data))
    app.state.pipeline_manager = None
    return TestClient(app)


def upload_dbc(client):
    return client.post(
        "/api/dbc/upload",
        files={"file": ("synthetic.dbc", SYNTHETIC_DBC, "application/octet-stream")},
    )


def definition(name="Bias_Test", **overrides):
    payload = {
        "name": name,
        "kind": "continuous",
        "category": "Brakes",
        "unit": "psi",
        "inputs": ["Brakes.Front_Psi", "Brakes.Rear_Psi"],
        "operations": [{"type": "combine", "operator": "add"}],
    }
    payload.update(overrides)
    return payload


class TestOperationsCatalog:
    def test_shape(self, client):
        response = client.get("/api/wts/operations")
        assert response.status_code == 200
        data = response.json()
        assert data["combine_operators"] == ["add", "subtract", "multiply", "divide"]
        assert {"type", "label", "is_head", "params"} <= set(
            data["operations"][0]
        )


class TestLegacyCompatibility:
    """I7: with a .dbc active and no WTS features used, old responses hold."""

    def test_dbc_listing_additive(self, client):
        upload_dbc(client)
        data = client.get("/api/dbc").json()
        assert data["active"] == "synthetic.dbc"
        entry = data["available"][0]
        assert {"name", "size", "mtime"} <= set(entry)
        assert entry["type"] == "dbc"

    def test_signals_legacy_fields(self, client):
        upload_dbc(client)
        data = client.get("/api/signals").json()
        legacy = {
            "id": "Brakes.Front_Psi", "node": "ECU", "message": "Brakes",
            "name": "Front_Psi", "unit": "psi",
        }
        assert legacy in data["signals"]

    def test_wts_signals_empty_without_setup(self, client):
        data = client.get("/api/wts/signals").json()
        assert data["signals"] == [] and data["issues"] == []


class TestCrud:
    def test_put_promotes_and_lists_under_wt_signals(self, client):
        upload_dbc(client)
        response = client.put(
            "/api/wts/signals/Bias_Test",
            json={"definition": definition()},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["promoted_to"] == "synthetic.wts"
        assert result["def_hash"] and result["wts_version"] >= 2

        signals = client.get("/api/signals").json()["signals"]
        virtual = next(s for s in signals if s["id"] == "WTS.Bias_Test")
        assert virtual["node"] == "WT Signals"
        assert virtual["message"] == "Brakes"
        assert virtual["is_virtual"] is True
        assert virtual["broken"] is False
        assert virtual["operations"] == [{"type": "combine", "operator": "add"}]

    def test_put_validation_422(self, client):
        upload_dbc(client)
        response = client.put(
            "/api/wts/signals/Bad",
            json={"definition": definition("Bad", inputs=["Ghost.Signal"])},
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["errors"][0]["code"] == "input_unknown"
        assert detail["errors"][0]["signal"] == "Bad"

    def test_put_kind_event_422(self, client):
        upload_dbc(client)
        response = client.put(
            "/api/wts/signals/Bad",
            json={"definition": definition("Bad", kind="event")},
        )
        assert response.status_code == 422
        assert "not supported yet" in response.json()["detail"]["errors"][0]["message"]

    def test_put_name_mismatch_422(self, client):
        upload_dbc(client)
        response = client.put(
            "/api/wts/signals/Other", json={"definition": definition()}
        )
        assert response.status_code == 422
        assert response.json()["detail"]["errors"][0]["code"] == "name_mismatch"

    def test_put_unknown_op_422(self, client):
        upload_dbc(client)
        response = client.put(
            "/api/wts/signals/Bad",
            json={"definition": definition(
                "Bad", operations=[{"type": "teleport"}]
            )},
        )
        assert response.status_code == 422
        assert response.json()["detail"]["errors"][0]["code"] == "op_unknown"

    def test_get_signals_lists_broken(self, client):
        upload_dbc(client)
        # craft a .wts with a broken definition and upload it
        from wts.wts_file import WtsFile

        wts = WtsFile.from_dbc_bytes("mix", "mix.dbc", SYNTHETIC_DBC.encode())
        wts.raw_signals.append({"name": "Oops", "kind": "continuous",
                                "inputs": ["Ghost.X"], "operations": [{"type": "scale", "factor": 1}]})
        wts.raw_signal_indexes.append(0)
        wts.parse_errors.append({"signal": "Oops", "code": "op_unknown",
                                 "message": "unknown operation type 'teleport'"})
        client.post("/api/dbc/upload", files={
            "file": ("mix.wts", wts.serialize().encode(), "application/json")})
        client.post("/api/dbc/select", data={"filename": "mix.wts"})
        data = client.get("/api/wts/signals").json()
        broken = next(s for s in data["signals"] if s["name"] == "Oops")
        assert broken["broken"] is True
        assert any(issue["signal"] == "Oops" for issue in data["issues"])

    def test_delete_with_dependents_409(self, client):
        upload_dbc(client)
        client.put("/api/wts/signals/A", json={"definition": definition("A")})
        client.put("/api/wts/signals/B", json={"definition": definition(
            "B", inputs=["WTS.A"], operations=[{"type": "scale", "factor": 2}]
        )})
        response = client.delete("/api/wts/signals/A")
        assert response.status_code == 409
        assert response.json()["detail"] == {"dependents": ["B"]}
        assert client.delete("/api/wts/signals/B").status_code == 200
        assert client.delete("/api/wts/signals/Nope").status_code == 404


class TestSetupEndpoints:
    def test_download_roundtrip(self, client):
        upload_dbc(client)
        response = client.get("/api/dbc/synthetic.dbc/download")
        assert response.status_code == 200
        assert response.content == SYNTHETIC_DBC.encode()
        assert "attachment" in response.headers["content-disposition"]
        assert client.get("/api/dbc/nope.dbc/download").status_code == 404

    def test_wts_upload_rejects_invalid_400(self, client):
        response = client.post(
            "/api/dbc/upload",
            files={"file": ("bad.wts", b"{oops", "application/json")},
        )
        assert response.status_code == 400

    def test_wts_upload_collision_409(self, client):
        from wts.wts_file import WtsFile

        payload = WtsFile.from_dbc_bytes(
            "c", "c.dbc", SYNTHETIC_DBC.encode()
        ).serialize().encode()
        first = client.post(
            "/api/dbc/upload",
            files={"file": ("c.wts", payload, "application/json")},
        )
        assert first.status_code == 200
        second = client.post(
            "/api/dbc/upload",
            files={"file": ("c.wts", payload, "application/json")},
        )
        assert second.status_code == 409

    def test_rename_extension_change_400(self, client):
        upload_dbc(client)
        response = client.patch(
            "/api/dbc/synthetic.dbc", json={"new_name": "synthetic.wts"}
        )
        assert response.status_code == 400

    def test_rename_and_delete_wts(self, client):
        from wts.wts_file import WtsFile

        payload = WtsFile.from_dbc_bytes(
            "r", "r.dbc", SYNTHETIC_DBC.encode()
        ).serialize().encode()
        client.post("/api/dbc/upload", files={"file": ("r.wts", payload, "application/json")})
        assert client.patch("/api/dbc/r.wts", json={"new_name": "r2.wts"}).status_code == 200
        assert client.get("/api/dbc").json()["available"][0]["name"] == "r2.wts"
        assert client.delete("/api/dbc/r2.wts").status_code == 200

    def test_active_setup_path_flows_into_config(self, client):
        upload_dbc(client)
        client.put("/api/wts/signals/A", json={"definition": definition("A")})
        # Promotion switched the active setup to synthetic.wts; upload_config
        # (the route that records the path for the dashboard) must point at
        # the .wts, not the legacy .dbc directory.
        response = client.post("/api/upload_config", data={"source": "zmq"})
        assert response.status_code == 200
        config = client.get("/api/config").json()
        assert config["dbc_file"].endswith("synthetic.wts")
