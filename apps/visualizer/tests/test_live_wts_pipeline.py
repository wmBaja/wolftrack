"""PipelineManager live-path integration with virtual signals (Part 4.2-4.5).

FakeDataSource yields scripted can_batch messages encoded against the
synthetic DBC; a stub DBCManager supplies definitions and the hot-reload
version. ws_manager.subscribed_signals is set per test.
"""
import asyncio

import pytest

from config import AppConfig
from pipeline.manager import PipelineManager
from tests.helpers.fake_source import FakeDataSource
from tests.helpers.make_blf import synthetic_database
from wts.engine import VirtualSignalEngine
from wts.schema import OperationDef, VirtualSignalDef
import ws_manager as ws_module

manager = ws_module.manager


def scale(name, inputs, ops):
    return VirtualSignalDef(
        name=name,
        inputs=tuple(inputs),
        operations=tuple(
            OperationDef(o["type"], {k: v for k, v in o.items() if k != "type"})
            for o in ops
        ),
    )


TOTAL = scale("Total", ("Brakes.Front_Psi", "Brakes.Rear_Psi"),
              [{"type": "combine", "operator": "add"}])
AVG = scale("Avg", ("Brakes.Front_Psi",),
            [{"type": "moving_avg", "window_seconds": 1.0}])


def synthetic_database_as_text_with_extra():
    from tests.helpers.make_blf import SYNTHETIC_DBC

    return SYNTHETIC_DBC + """BO_ 300 Extra: 8 ECU
 SG_ RPM : 0|16@1+ (1,0) [0|65535] "rpm" Vector__XXX

"""


class StubWtsManager:
    def __init__(self, defs=None):
        self.db = synthetic_database()
        self.defs = list(defs or [])
        self.version = 1

    def get_active_dbc(self):
        return self.db

    def get_virtual_signals(self):
        return list(self.defs)

    def get_wts_version(self):
        return self.version

    def set_defs(self, defs):
        """Simulate an edit: definitions change and the version bumps."""
        self.defs = list(defs)
        self.version += 1


def brake_frames(times, front, rear):
    return [
        (t, "Brakes", {"Front_Psi": f, "Rear_Psi": r})
        for t, f, r in zip(times, front, rear)
    ]


async def run_pipeline(source, wts_manager, subscribed, *, mutate=None):
    """Run one pipeline session; return (payloads, pipeline)."""
    manager.subscribed_signals = set(subscribed)
    pipeline = PipelineManager(AppConfig(), wts_manager)
    pipeline.source = source
    payloads = []
    pipeline.on_batch = payloads.append

    async def stream():
        for message in source.messages:
            if mutate is not None:
                await mutate(message)
            yield message
        if source.hold_open:
            await asyncio.sleep(3600)

    source.stream = stream  # inject mutation point between batches
    pipeline._task = asyncio.create_task(pipeline._run_loop())
    try:
        await asyncio.wait_for(asyncio.shield(pipeline._task), timeout=5)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        pipeline._task.cancel()
        try:
            await pipeline._task
        except asyncio.CancelledError:
            pass
    return payloads, pipeline


def brake_frames_batches(n=5, dropped=0):
    times = [1000.0 + i * 0.1 for i in range(n)]
    frames = brake_frames(times, [10.0 + i for i in range(n)], [1.0] * n)
    return [(frames[:2], dropped), (frames[2:], 0)]


@pytest.fixture(autouse=True)
def _clear_subs():
    manager.subscribed_signals = set()
    yield
    manager.subscribed_signals = set()


class TestUpstreamDecoding:
    def test_only_wts_subscribed_still_decodes_raw_inputs(self):
        source = FakeDataSource(brake_frames_batches())
        payloads, _ = asyncio.run(run_pipeline(
            source, StubWtsManager([TOTAL]), {"WTS.Total"}))
        signals = {}
        for payload in payloads:
            for sid, series in payload["signals"].items():
                signals.setdefault(sid, []).extend(
                    zip(series["timestamps"], series["values"]))
        assert set(signals) == {"WTS.Total"}  # raw not charted, WTS is
        values = [v for _, v in signals["WTS.Total"]]
        assert values[0] == pytest.approx(11.0)
        assert values[-1] == pytest.approx(15.0)

    def test_fast_path_no_defs_ignores_raw_inputs(self):
        source = FakeDataSource(brake_frames_batches())
        payloads, pipeline = asyncio.run(run_pipeline(
            source, StubWtsManager([]), {"WTS.Total"}))
        # no definitions: nothing decodes, nothing emitted (I9)
        assert pipeline.wts_runtime is None
        assert payloads == []


class TestAlwaysOn:
    def test_state_accumulates_before_subscribe(self):
        # Subscribe only from batch 2 on: Avg must still reflect batch 1.
        calls = {"n": 0}

        async def mutate(message):
            calls["n"] += 1
            if calls["n"] == 2:
                manager.subscribed_signals = {"WTS.Avg"}

        source = FakeDataSource(brake_frames_batches(n=6))
        payloads, _ = asyncio.run(run_pipeline(
            source, StubWtsManager([AVG]), set(), mutate=mutate))
        emitted = [v for p in payloads for v in p["signals"].get("WTS.Avg", {}).get("values", [])]
        assert emitted, "expected output after late subscription"
        # consistency: last emitted equals mean of ALL 6 front values seen,
        # including the batch-1 samples that predate the subscription
        fronts = [10.0 + i for i in range(6)]
        assert emitted[-1] == pytest.approx(sum(fronts) / len(fronts))


class TestDeliveryIndependence:
    def test_live_matches_run_batch(self):
        frames = brake_frames(
            [1000.0 + i * 0.05 for i in range(50)],
            [(i * 7) % 23 for i in range(50)],
            [(i * 5) % 13 for i in range(50)],
        )
        defs = [TOTAL, AVG,
                scale("Twice", ("WTS.Total",), [{"type": "scale", "factor": 2}])]
        source = FakeDataSource([(frames[:20], 0), (frames[20:35], 0), (frames[35:], 0)])
        payloads, _ = asyncio.run(run_pipeline(
            source, StubWtsManager(defs),
            {"WTS.Total", "WTS.Avg", "WTS.Twice"}))
        live = {}
        for payload in payloads:
            for sid, series in payload["signals"].items():
                live.setdefault(sid, []).extend(
                    zip(series["timestamps"], series["values"]))

        from wts.batch import run_batch

        engine = VirtualSignalEngine(defs)
        rows = []
        for t, _name, values in frames:
            for sig, value in values.items():
                rows.append((t, f"Brakes.{sig}", value))
        batch = {}
        for ts, sid, value in run_batch(engine, rows):
            batch.setdefault(sid, []).append((ts, value))

        for sid in live:
            assert live[sid] == batch[sid], sid


class TestNoWtsNoChange:
    def test_raw_only_stream_identical(self):
        # Baseline behavior (I7): subscribe raw only, no defs -> same
        # payloads as before this feature existed.
        source = FakeDataSource([([(1000.0, "Brakes", {"Front_Psi": 12.0, "Rear_Psi": 3.0})], 0)])
        payloads, _ = asyncio.run(run_pipeline(
            source, StubWtsManager([]), {"Brakes.Front_Psi"}))
        assert len(payloads) == 1
        payload = payloads[0]
        assert set(payload) == {"type", "signals", "dropped_batches"}
        assert "clock_step" not in payload
        series = payload["signals"]["Brakes.Front_Psi"]
        assert series["values"] == [12.0]


class TestHotReload:
    def test_midstream_definition_edit_appears(self):
        calls = {"n": 0}
        wts = StubWtsManager([TOTAL])

        async def mutate(message):
            calls["n"] += 1
            if calls["n"] == 2:
                wts.set_defs([TOTAL, AVG])

        source = FakeDataSource(brake_frames_batches(n=6))
        payloads, pipeline = asyncio.run(run_pipeline(
            source, wts, {"WTS.Total", "WTS.Avg"}, mutate=mutate))
        emitted_ids = {sid for p in payloads for sid in p["signals"]}
        assert {"WTS.Total", "WTS.Avg"} <= emitted_ids
        assert pipeline.wts_runtime.version == wts.version

    def test_dbc_switch_refreshes_arb_cache(self):
        # Add a message to the DBC mid-session; frames of the new id must
        # decode after the version bump (arb_id_cache refresh).
        from tests.helpers.fake_source import encode_frame_dict

        import cantools

        extra_db = cantools.database.load_string(
            synthetic_database_as_text_with_extra(), database_format="dbc")

        calls = {"n": 0}
        wts = StubWtsManager([])

        async def stream():
            yield {"type": "can_batch", "frames": [
                encode_frame_dict(1000.0, "Brakes", {"Front_Psi": 1.0, "Rear_Psi": 2.0}, extra_db)],
                "dropped_batches": 0}
            calls["n"] += 1
            wts.db = extra_db
            wts.version += 1
            manager.subscribed_signals = {"Extra.RPM"}
            yield {"type": "can_batch", "frames": [
                encode_frame_dict(1000.1, "Extra", {"RPM": 5000.0}, extra_db)],
                "dropped_batches": 0}

        async def main():
            manager.subscribed_signals = {"Brakes.Front_Psi"}
            pipeline = PipelineManager(AppConfig(), wts)
            pipeline.source = FakeDataSource([])
            pipeline.source.stream = stream
            payloads = []
            pipeline.on_batch = payloads.append
            task = asyncio.create_task(pipeline._run_loop())
            await asyncio.wait_for(asyncio.shield(task), timeout=5)
            return payloads

        payloads = asyncio.run(main())
        emitted = {sid for p in payloads for sid in p["signals"]}
        assert {"Brakes.Front_Psi", "Extra.RPM"} == emitted


class TestClockStepsAndGaps:
    def _batches(self):
        return [
            ([(1000.0, "Brakes", {"Front_Psi": 10.0, "Rear_Psi": 1.0}),
              (1001.0, "Brakes", {"Front_Psi": 20.0, "Rear_Psi": 1.0})], 0),
            # clock step: 3 s backward (looped replay / DAQ reboot)
            ([(998.0, "Brakes", {"Front_Psi": 5.0, "Rear_Psi": 1.0})], 0),
            # 50 ms backward jitter: skipped, no reset
            ([(997.95, "Brakes", {"Front_Psi": 7.0, "Rear_Psi": 1.0})], 0),
            # forward jump: gap, not a reset
            ([(1030.0, "Brakes", {"Front_Psi": 9.0, "Rear_Psi": 1.0})], 0),
        ]

    def test_clock_step_flag_and_resume(self):
        source = FakeDataSource(self._batches())
        payloads, pipeline = asyncio.run(run_pipeline(
            source, StubWtsManager([AVG]), {"WTS.Avg"}))
        flagged = [p for p in payloads if p.get("clock_step")]
        assert len(flagged) == 1
        # the flagged batch carries the post-step value, resumed immediately
        assert 5.0 in flagged[0]["signals"]["WTS.Avg"]["values"]
        stats = pipeline.wts_runtime.stats()
        assert stats["clock_steps"] == 1
        # the step flushes the old-time-base batch first: each array stays
        # non-decreasing, and the flagged batch is on the new base only
        flagged = flagged[0]
        assert flagged["signals"]["WTS.Avg"]["timestamps"] == [998.0, 1030.0]
        assert flagged["signals"]["WTS.Avg"]["values"] == [5.0, 9.0]
        for payload in payloads:
            stamps = payload["signals"]["WTS.Avg"]["timestamps"]
            assert stamps == sorted(stamps)

    def test_dropped_batches_trigger_gap(self):
        source = FakeDataSource([
            ([(1000.0, "Brakes", {"Front_Psi": 10.0, "Rear_Psi": 1.0})], 0),
            # dropped data happened before this batch: the 10.0 sample must
            # be discarded even though timestamps look continuous
            ([(1000.5, "Brakes", {"Front_Psi": 20.0, "Rear_Psi": 1.0})], 3),
        ])
        payloads, _ = asyncio.run(run_pipeline(
            source, StubWtsManager([AVG]), {"WTS.Avg"}))
        values = [v for p in payloads for v in p["signals"]["WTS.Avg"]["values"]]
        assert values == [10.0, 20.0]  # not 15.0: gap cleared the old sample
        assert any(p["dropped_batches"] == 3 for p in payloads)


class TestMissingTimestamp:
    def test_skipped_for_wts_warn_once(self, caplog):
        import logging

        source = FakeDataSource([
            ([(None, "Brakes", {"Front_Psi": 10.0, "Rear_Psi": 1.0})], 0),
            ([(1000.0, "Brakes", {"Front_Psi": 20.0, "Rear_Psi": 1.0})], 0),
        ])
        with caplog.at_level(logging.WARNING, logger="pipeline.manager"):
            payloads, pipeline = asyncio.run(run_pipeline(
                source, StubWtsManager([TOTAL]), {"WTS.Total"}))
        values = [v for p in payloads for v in p["signals"]["WTS.Total"]["values"]]
        assert values == [21.0]  # only the timestamped frame produced output
        warnings = [r for r in caplog.records
                    if "without a timestamp" in r.getMessage()]
        assert len(warnings) == 1
        assert pipeline.wts_runtime.stats()["missing_timestamps"] == 1


class TestFailureIsolation:
    def test_engine_error_does_not_kill_loop(self, monkeypatch):
        import wts.live as live_module

        original = live_module.LiveWtsRuntime.process
        calls = {"n": 0}

        def flaky(self, ts, values):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("boom")
            return original(self, ts, values)

        monkeypatch.setattr(live_module.LiveWtsRuntime, "process", flaky)
        source = FakeDataSource([
            ([(1000.0, "Brakes", {"Front_Psi": 10.0, "Rear_Psi": 1.0})], 0),
            ([(1000.1, "Brakes", {"Front_Psi": 20.0, "Rear_Psi": 1.0})], 0),
            ([(1000.2, "Brakes", {"Front_Psi": 30.0, "Rear_Psi": 1.0})], 0),
        ])
        payloads, _ = asyncio.run(run_pipeline(
            source, StubWtsManager([TOTAL]), {"WTS.Total"}))
        values = [v for p in payloads for v in p["signals"]["WTS.Total"]["values"]]
        assert values == [11.0, 31.0]  # frame 2 skipped, 1 and 3 present


class TestReset:
    def test_new_session_clears_state(self):
        wts_manager = StubWtsManager([AVG])
        source1 = FakeDataSource(
            [([(1000.0, "Brakes", {"Front_Psi": 10.0, "Rear_Psi": 1.0})], 0)])
        asyncio.run(run_pipeline(source1, wts_manager, {"WTS.Avg"}))
        source2 = FakeDataSource(
            [([(2000.0, "Brakes", {"Front_Psi": 50.0, "Rear_Psi": 1.0})], 0)])
        payloads, pipeline = asyncio.run(run_pipeline(source2, wts_manager, {"WTS.Avg"}))
        values = [v for p in payloads for v in p["signals"]["WTS.Avg"]["values"]]
        assert values == [50.0]  # 10.0 from the previous session is gone


class TestSubscriptionChanges:
    def test_emit_follows_subscription_not_computation(self):
        calls = {"n": 0}

        async def mutate(message):
            calls["n"] += 1
            if calls["n"] == 2:
                manager.subscribed_signals = set()  # everyone unsubscribes

        source = FakeDataSource(brake_frames_batches(n=6))
        payloads, pipeline = asyncio.run(run_pipeline(
            source, StubWtsManager([AVG]), {"WTS.Avg"}, mutate=mutate))
        emitted_values = [v for p in payloads
                          for v in p["signals"].get("WTS.Avg", {}).get("values", [])]
        assert emitted_values == [10.0, 10.5]  # only batch-1 frames were charted
        # computation kept running regardless: the engine holds the last
        # front value from the final (unsubscribed) frame
        assert pipeline.wts_runtime.engine._values["Brakes.Front_Psi"] == 15.0
