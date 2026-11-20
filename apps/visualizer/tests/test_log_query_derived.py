"""Part 3: derived virtual signals over SQLite-indexed .blf logs.

Covers: delivery independence (I1), DBC-aware cache keys, edit-without-
re-parse (I3), stale-cache across restarts, dependency invalidation and
subgraph isolation (I4), atomic swaps, cancellation, pending semantics,
removed definitions.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time

import pytest

from pipeline.log_query import LogQueryService
from tests.helpers.make_blf import SYNTHETIC_DBC, synthetic_database
from wts.schema import OperationDef, VirtualSignalDef


def wait_for(service, predicate, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = service.get_status()
        if predicate(status):
            return status
        time.sleep(0.02)
    raise AssertionError(f"condition not met; last status: {service.get_status()}")


def scale_sig(name, inputs, ops, **kw):
    return VirtualSignalDef(
        name=name,
        inputs=tuple(inputs),
        operations=tuple(
            OperationDef(type=o["type"], params={k: v for k, v in o.items() if k != "type"})
            for o in ops
        ),
        **kw,
    )


def frames(count=20, base=100.0):
    return [
        (base + index * 0.1, "Brakes",
         {"Front_Psi": 100.0 + index, "Rear_Psi": 50.0 + index * 2})
        for index in range(count)
    ]


class Harness:
    """Service + mutable definitions provider, mimicking DBCManager wiring."""

    def __init__(self, tmp_path, synthetic_blf):
        self.definitions: list[VirtualSignalDef] = []
        self.service = LogQueryService(tmp_path / "cache")
        self.service.set_definitions_provider(
            lambda: (list(self.definitions), self._hashes())
        )
        self.blf = synthetic_blf(frames())

    def _hashes(self):
        from wts.graph import compute_definition_hashes, topological_order

        order, _ = topological_order(self.definitions)
        return compute_definition_hashes(self.definitions, order)

    def start(self, dbc=None):
        self.service.start_indexing(self.blf, dbc or synthetic_database(), "d" * 32)

    def wait_ready(self):
        wait_for(self.service, lambda s: s["status"] == "ready")

    def wait_derived_settled(self):
        wait_for(
            self.service,
            lambda s: s["derived"]["status"] in ("ready", "idle", "error"),
        )

    def wait_until(self, predicate, timeout=10):
        """Poll an arbitrary predicate against live service state."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return True
            time.sleep(0.02)
        raise AssertionError(f"condition not met: {self.service.get_status()}")

    def wait_query_value(self, signal_id, first_value, length=None):
        def check():
            data = self.service.query([signal_id], -1, 5, 100)
            values = data[signal_id]["values"]
            if not values or values[0] != pytest.approx(first_value):
                return False
            return length is None or len(values) == length
        self.wait_until(check)

    def recompute(self):
        self.service.RECOMPUTE_DEBOUNCE_SECONDS = 0.0
        self.service.request_wts_recompute()


@pytest.fixture
def harness(tmp_path, synthetic_blf):
    return Harness(tmp_path, synthetic_blf)


class TestDerivedCompute:
    def test_total_computed_on_index(self, harness):
        harness.definitions.append(scale_sig(
            "Total", ["Brakes.Front_Psi", "Brakes.Rear_Psi"],
            [{"type": "combine", "operator": "add"}]))
        harness.start()
        harness.wait_ready()
        # First frame: 100 + 50 = 150; second: 101 + 52 = 153; 20 rows total.
        harness.wait_query_value("WTS.Total", 150.0, length=20)
        data = harness.service.query(["WTS.Total"], -1, 5, 100)
        assert data["WTS.Total"]["values"][1] == 153.0

    def test_delivery_independence_vs_run_batch(self, harness):
        """I1: log-path derived rows == feeding the same rows through run_batch."""
        from wts.batch import run_batch
        from wts.engine import VirtualSignalEngine

        harness.definitions.extend([
            scale_sig("Total", ["Brakes.Front_Psi", "Brakes.Rear_Psi"],
                      [{"type": "combine", "operator": "add"}]),
            scale_sig("Bias", ["Brakes.Front_Psi", "WTS.Total"],
                      [{"type": "combine", "operator": "divide"},
                       {"type": "scale", "factor": 100}]),
        ])
        harness.start()
        harness.wait_ready()
        harness.wait_derived_settled()

        db_path = harness.service.db_path
        connection = sqlite3.connect(db_path)
        rows = sorted(
            ((ts, sid, value) for ts, sid, value in connection.execute(
                "SELECT timestamp, signal_id, value FROM signals")),
            key=lambda row: row[0],
        )
        expected: dict[str, list] = {}
        for ts, sid, value in run_batch(
            VirtualSignalEngine(list(harness.definitions)), rows
        ):
            expected.setdefault(sid, []).append((ts, value))

        for sid, series in expected.items():
            stored = connection.execute(
                "SELECT timestamp, value FROM derived_signals WHERE signal_id = ? "
                "ORDER BY timestamp", (sid,),
            ).fetchall()
            assert [round(v, 9) for _, v in stored] == [
                round(v, 9) for _, v in series
            ]
            assert [round(t, 9) for t, _ in stored] == [round(t, 9) for t, _ in series]
        connection.close()

    def test_pending_semantics(self, harness, monkeypatch):
        harness.definitions.append(scale_sig(
            "Total", ["Brakes.Front_Psi"], [{"type": "scale", "factor": 2}]))
        # Pause mid-compute: the engine batch loop runs; hook run_batch.
        import pipeline.log_query as module

        real_run_batch = module.run_batch
        gate = threading.Event()

        def gating(engine, rows):
            for row in real_run_batch(engine, rows):
                yield row
            gate.wait(timeout=5)

        monkeypatch.setattr(module, "run_batch", gating)
        harness.start()
        harness.wait_ready()
        wait_for(harness.service, lambda s: s["derived"]["status"] == "computing")
        data = harness.service.get_results(["WTS.Total"], -1, 5, 100)
        assert "WTS.Total" in data[1]
        assert data[0]["WTS.Total"]["values"] == []
        gate.set()
        harness.wait_query_value("WTS.Total", 200.0)
        data = harness.service.get_results(["WTS.Total"], -1, 5, 100)
        assert data[1] == []


class TestCacheKeys:
    def test_different_dbc_different_file_no_reread(self, tmp_path, synthetic_blf):
        blf = synthetic_blf(frames())

        db_a = synthetic_database()
        service = LogQueryService(tmp_path / "cache")
        service.start_indexing(blf, db_a, "aaaa" * 16)
        wait_for(service, lambda s: s["status"] == "ready")
        files_a = set(p.name for p in (tmp_path / "cache").glob("*.sqlite"))
        service.stop()

        service2 = LogQueryService(tmp_path / "cache")
        service2.start_indexing(blf, db_a, "bbbb" * 16)
        wait_for(service2, lambda s: s["status"] in ("ready", "error"))
        files_b = set(p.name for p in (tmp_path / "cache").glob("*.sqlite"))
        assert files_a != files_b
        service2.stop()

        # Switching back: cached path must be taken (BLFReader must not run).
        import can
        real_reader = can.BLFReader

        def forbidden(*args, **kwargs):
            raise AssertionError("BLF must not be re-parsed for a cached pair")

        can.BLFReader = forbidden
        try:
            service3 = LogQueryService(tmp_path / "cache")
            service3.start_indexing(blf, db_a, "aaaa" * 16)
            wait_for(service3, lambda s: s["status"] == "ready")
            service3.stop()
        finally:
            can.BLFReader = real_reader

    def test_nodbc_key_used_when_missing(self, tmp_path, synthetic_blf):
        blf = synthetic_blf(frames())
        service = LogQueryService(tmp_path / "cache")
        service.start_indexing(blf, None)  # no DBC: worker errors (as before)
        wait_for(service, lambda s: s["status"] == "error")
        assert "nodbc" in os.path.basename(service.db_path)
        service.stop()


class TestEdits:
    def test_edit_after_index_no_reparse(self, harness, monkeypatch):
        """I3: after raw publish, a WTS edit never re-reads the BLF and never
        touches the raw signals table."""
        harness.start()
        harness.wait_ready()
        connection = sqlite3.connect(harness.service.db_path)
        raw_before = connection.execute(
            "SELECT COUNT(*), SUM(value) FROM signals").fetchone()

        import can
        real_reader = can.BLFReader

        def forbidden(*args, **kwargs):
            raise AssertionError("edit must not re-parse the BLF")

        can.BLFReader = forbidden
        try:
            harness.definitions.append(scale_sig(
                "Total", ["Brakes.Front_Psi", "Brakes.Rear_Psi"],
                [{"type": "combine", "operator": "add"}]))
            harness.recompute()
            harness.wait_query_value("WTS.Total", 150.0, length=20)
        finally:
            can.BLFReader = real_reader
        assert connection.execute(
            "SELECT COUNT(*), SUM(value) FROM signals").fetchone() == raw_before
        connection.close()

    def test_cosmetic_edit_does_not_recompute(self, harness):
        harness.definitions.append(scale_sig(
            "Total", ["Brakes.Front_Psi"], [{"type": "scale", "factor": 2}]))
        harness.start()
        harness.wait_ready()
        harness.wait_derived_settled()
        connection = sqlite3.connect(harness.service.db_path)
        computed_before = connection.execute(
            "SELECT computed_at, row_count FROM derived_meta WHERE signal_id='WTS.Total'"
        ).fetchone()

        harness.definitions[0] = scale_sig(
            "Total", ["Brakes.Front_Psi"], [{"type": "scale", "factor": 2}],
            unit="psi", category="Brakes", description="pretty")
        harness.recompute()
        harness.wait_until(lambda: harness.service.get_status()["derived"]["status"]
                           == "computing" or harness.service.get_status()["derived"]["status"] == "ready")
        harness.wait_derived_settled()
        computed_after = connection.execute(
            "SELECT computed_at, row_count FROM derived_meta WHERE signal_id='WTS.Total'"
        ).fetchone()
        assert computed_after == computed_before  # no recompute happened
        connection.close()

    def test_dependency_invalidation_and_isolation(self, harness):
        """I4: editing WTS.A recomputes WTS.B (computed_at changes) but an
        unrelated signal sharing raw inputs is untouched."""
        a = scale_sig("A", ["Brakes.Front_Psi"], [{"type": "scale", "factor": 2}])
        b = scale_sig("B", ["WTS.A"], [{"type": "bias", "offset": 1}])
        unrelated = scale_sig("U", ["Brakes.Rear_Psi"],
                              [{"type": "scale", "factor": 3}])
        harness.definitions.extend([a, b, unrelated])
        harness.start()
        harness.wait_ready()
        harness.wait_derived_settled()

        connection = sqlite3.connect(harness.service.db_path)
        before = dict(connection.execute(
            "SELECT signal_id, computed_at FROM derived_meta").fetchall())
        assert set(before) == {"WTS.A", "WTS.B", "WTS.U"}

        harness.definitions = [
            scale_sig("A", ["Brakes.Front_Psi"], [{"type": "scale", "factor": 5}]),
            b, unrelated,
        ]
        harness.recompute()
        # First sample after the edit: 100*5+1 = 501
        harness.wait_query_value("WTS.B", 501.0)
        after = dict(connection.execute(
            "SELECT signal_id, computed_at FROM derived_meta").fetchall())
        assert after["WTS.A"] != before["WTS.A"]
        assert after["WTS.B"] != before["WTS.B"]
        assert after["WTS.U"] == before["WTS.U"]
        connection.close()

    def test_stale_across_restart(self, tmp_path, synthetic_blf):
        blf = synthetic_blf(frames())
        definitions = [scale_sig(
            "Total", ["Brakes.Front_Psi"], [{"type": "scale", "factor": 2}])]

        def provider():
            from wts.graph import compute_definition_hashes, topological_order
            order, _ = topological_order(definitions)
            return list(definitions), compute_definition_hashes(definitions, order)

        service = LogQueryService(tmp_path / "cache")
        service.set_definitions_provider(provider)
        service.start_indexing(blf, synthetic_database(), "h" * 32)
        wait_for(service, lambda s: s["status"] == "ready")
        deadline = time.time() + 10
        while time.time() < deadline and service.query(["WTS.Total"], -1, 5, 100)["WTS.Total"]["values"] == []:
            time.sleep(0.02)
        assert service.query(["WTS.Total"], -1, 5, 100)["WTS.Total"]["values"][0] == 200.0
        service.stop()

        # "Edit on disk": change the definition, new service over same cache.
        definitions[0] = scale_sig(
            "Total", ["Brakes.Front_Psi"], [{"type": "scale", "factor": 3}])
        service2 = LogQueryService(tmp_path / "cache")
        service2.set_definitions_provider(provider)
        service2.start_indexing(blf, synthetic_database(), "h" * 32)
        wait_for(service2, lambda s: s["status"] == "ready")
        # After the recompute triggered on open the value is 300 — and the
        # stale 200 from the cache is replaced atomically, never mixed.
        deadline = time.time() + 10
        while time.time() < deadline:
            values = service2.query(["WTS.Total"], -1, 5, 100)["WTS.Total"]["values"]
            if len(values) == 20 and values[0] == 300.0:
                break
            assert all(v in (200.0, 300.0) for v in values)  # old complete or new complete
            time.sleep(0.02)
        else:
            raise AssertionError("recompute did not converge")
        service2.stop()

    def test_removed_definition_cleans_rows(self, harness):
        harness.definitions.append(scale_sig(
            "Total", ["Brakes.Front_Psi"], [{"type": "scale", "factor": 2}]))
        harness.start()
        harness.wait_ready()
        harness.wait_derived_settled()
        connection = sqlite3.connect(harness.service.db_path)
        assert connection.execute(
            "SELECT COUNT(*) FROM derived_signals").fetchone()[0] > 0

        harness.definitions = []
        harness.recompute()
        harness.wait_until(lambda: connection.execute(
            "SELECT COUNT(*) FROM derived_signals").fetchone()[0] == 0)
        assert connection.execute(
            "SELECT COUNT(*) FROM derived_meta").fetchone()[0] == 0
        connection.close()


class TestCancellation:
    def test_cancel_keeps_previous_rows(self, harness, monkeypatch):
        harness.definitions.append(scale_sig(
            "Total", ["Brakes.Front_Psi"], [{"type": "scale", "factor": 2}]))
        harness.start()
        harness.wait_ready()
        harness.wait_derived_settled()
        connection = sqlite3.connect(harness.service.db_path)
        rows_before = connection.execute(
            "SELECT COUNT(*) FROM derived_signals WHERE signal_id='WTS.Total'"
        ).fetchone()[0]

        # Second compute cancelled mid-stream by stop(); rows must survive.
        harness.definitions = [scale_sig(
            "Total", ["Brakes.Front_Psi"], [{"type": "scale", "factor": 9}])]
        import pipeline.log_query as module
        real_run_batch = module.run_batch

        def slow(engine, rows):
            count = 0
            for row in real_run_batch(engine, rows):
                count += 1
                if count == 3:
                    harness.service.stop()  # cancels the compute
                    time.sleep(0.05)
                yield row

        monkeypatch.setattr(module, "run_batch", slow)
        harness.service.RECOMPUTE_DEBOUNCE_SECONDS = 0.0
        harness.service.request_wts_recompute()
        time.sleep(0.4)
        rows_after = connection.execute(
            "SELECT COUNT(*) FROM derived_signals WHERE signal_id='WTS.Total'"
        ).fetchone()[0]
        assert rows_after == rows_before  # old rows intact
        connection.close()


class TestConcurrency:
    def test_raw_query_not_blocked_during_compute(self, harness, monkeypatch):
        harness.definitions.append(scale_sig(
            "Total", ["Brakes.Front_Psi", "Brakes.Rear_Psi"],
            [{"type": "combine", "operator": "add"},
             {"type": "moving_avg", "window_seconds": 5}]))
        import pipeline.log_query as module
        real_run_batch = module.run_batch
        release = threading.Event()

        def gating(engine, rows):
            for row in real_run_batch(engine, rows):
                yield row
            release.wait(timeout=5)

        monkeypatch.setattr(module, "run_batch", gating)
        harness.start()
        harness.wait_ready()

        deadline = time.time() + 5
        while time.time() < deadline:
            if harness.service.get_status()["derived"]["status"] == "computing":
                break
            time.sleep(0.01)
        started = time.perf_counter()
        data = harness.service.query(["Brakes.Front_Psi"], -1, 5, 100)
        elapsed = time.perf_counter() - started
        assert len(data["Brakes.Front_Psi"]["values"]) == 20
        assert elapsed < 1.0  # raw reads are not serialized behind compute
        release.set()
        harness.wait_derived_settled()
