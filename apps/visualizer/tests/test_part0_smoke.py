"""Part 0 smoke: the test helpers build a BLF that the indexer can consume."""
from __future__ import annotations

import can
import pytest

from pipeline.log_query import LogQueryService


def test_make_blf_roundtrips_through_python_can(synthetic_blf, synthetic_dbc):
    path = synthetic_blf(
        [
            (1.0, "Brakes", {"Front_Psi": 100.0, "Rear_Psi": 50.0}),
            (1.1, "Steering", {"Angle": 12.5}),
        ]
    )
    messages = list(can.BLFReader(path))
    assert len(messages) == 2
    decoded = synthetic_dbc.decode_message(
        messages[0].arbitration_id, messages[0].data
    )
    assert decoded == pytest.approx({"Front_Psi": 100.0, "Rear_Psi": 50.0})


def test_log_query_service_indexes_synthetic_blf(synthetic_blf, synthetic_dbc, tmp_path):
    path = synthetic_blf(
        [
            (10.0, "Brakes", {"Front_Psi": 200.0, "Rear_Psi": 80.0}),
            (10.5, "Brakes", {"Front_Psi": 300.0, "Rear_Psi": 120.0}),
        ]
    )
    service = LogQueryService(tmp_path / "cache")
    service.start_indexing(path, synthetic_dbc)
    service._task.join(timeout=10)

    status = service.get_status()
    assert status["status"] == "ready"
    # Bucket size 0.5 keeps the two samples in distinct buckets.
    data = service.query(["Brakes.Front_Psi"], 0, 100, 200)
    assert data["Brakes.Front_Psi"]["values"] == [200.0, 300.0]
    service.stop()
