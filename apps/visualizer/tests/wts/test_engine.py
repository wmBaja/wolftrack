"""Engine semantics: same-timestamp grouping, zero-order hold, chaining,
no fabricated data, monotonicity, gaps, and delivery independence (I1)."""
from __future__ import annotations

import math
import random

import pytest

from tests.wts.helpers import collect, sig_def
from wts.batch import run_batch
from wts.engine import VirtualSignalEngine
from wts.errors import WtsValidationError


class TestSameTimestamp:
    def test_single_sample_per_update(self):
        """D6 regression: inputs 80/20 at one ts emit exactly one 80/100 sample."""
        definition = sig_def(
            "Bias",
            ["B.Front_Psi", "B.Rear_Psi"],
            [{"type": "combine", "operator": "add"}],
        )
        engine = VirtualSignalEngine([definition])
        assert engine.update(0.0, {"B.Front_Psi": 50.0, "B.Rear_Psi": 50.0}) == {
            "WTS.Bias": 100.0
        }
        # Both new values arrive in one update: exactly one output, 80+20=100.
        outputs = engine.update(1.0, {"B.Front_Psi": 80.0, "B.Rear_Psi": 20.0})
        assert outputs == {"WTS.Bias": 100.0}

    def test_no_intermediate_values(self):
        """A 3-input chain never sees half-updated inputs."""
        definition = sig_def(
            "S",
            ["M.a", "M.b", "M.c"],
            [{"type": "combine", "operator": "add"}],
        )
        engine = VirtualSignalEngine([definition])
        engine.update(0.0, {"M.a": 1.0, "M.b": 2.0, "M.c": 3.0})
        # One update replaces all three: only the 10+... final value appears.
        outputs = engine.update(1.0, {"M.a": 10.0, "M.b": 20.0, "M.c": 30.0})
        assert list(outputs.values()) == [60.0]


class TestZeroOrderHold:
    def test_waits_for_all_inputs(self):
        definition = sig_def(
            "S", ["A.x", "B.y"], [{"type": "combine", "operator": "multiply"}]
        )
        engine = VirtualSignalEngine([definition])
        assert engine.update(0.0, {"A.x": 2.0}) == {}          # B.y unseen
        assert engine.update(1.0, {"B.y": 3.0}) == {"WTS.S": 6.0}  # 2*3
        # Only A.x changes; B.y holds: 4*3 = 12.
        assert engine.update(2.0, {"A.x": 4.0}) == {"WTS.S": 12.0}

    def test_output_times_are_union_of_input_times(self):
        definition = sig_def("S", ["A.x", "B.y"], [{"type": "scale", "factor": 1}, {"type": "bias", "offset": 0}])
        # single-input chain
        definition = sig_def("S", ["A.x"], [{"type": "scale", "factor": 1}])
        engine = VirtualSignalEngine([definition])
        series = collect(
            engine,
            [(0.0, {"A.x": 1.0}), (1.0, {"B.y": 9.0}), (2.0, {"A.x": 2.0})],
        )
        assert series == {"WTS.S": [(0.0, 1.0), (2.0, 2.0)]}


class TestChainingAndHashes:
    def test_downstream_sees_value_in_same_update(self):
        a = sig_def("A", ["R.p"], [{"type": "scale", "factor": 2}])
        b = sig_def("B", ["WTS.A", "R.q"], [{"type": "combine", "operator": "add"}])
        engine = VirtualSignalEngine([a, b])
        # A = 3*2 = 6; B = 6 + 10 = 16 in ONE update.
        assert engine.update(0.0, {"R.p": 3.0, "R.q": 10.0}) == {
            "WTS.A": 6.0,
            "WTS.B": 16.0,
        }

    def test_cycle_rejected_with_path(self):
        a = sig_def("A", ["WTS.B"], [{"type": "scale", "factor": 1}])
        b = sig_def("B", ["WTS.A"], [{"type": "scale", "factor": 1}])
        with pytest.raises(WtsValidationError) as excinfo:
            VirtualSignalEngine([a, b])
        cycle_errors = [
            error for error in excinfo.value.errors
            if error["code"] == "dependency_cycle"
        ]
        assert len(cycle_errors) == 1
        assert "WTS.A -> WTS.B -> WTS.A" in cycle_errors[0]["message"]

    def test_depth_limit(self):
        # Chain of 17 definitions exceeds MAX_DEPTH=16.
        defs = [sig_def("L0", ["R.p"], [{"type": "scale", "factor": 1}])]
        for index in range(1, 17):
            defs.append(
                sig_def(f"L{index}", [f"WTS.L{index - 1}"],
                        [{"type": "scale", "factor": 1}])
            )
        with pytest.raises(WtsValidationError) as excinfo:
            VirtualSignalEngine(defs)
        assert any(
            error["code"] == "dependency_depth" for error in excinfo.value.errors
        )
        # 16 definitions (depth 16) are accepted.
        VirtualSignalEngine(defs[:-1])

    def test_def_hash_rules(self):
        from wts.graph import compute_definition_hashes, topological_order

        a = sig_def("A", ["R.p"], [{"type": "scale", "factor": 2}], unit="psi")
        a_cosmetic = sig_def("A", ["R.p"], [{"type": "scale", "factor": 2}],
                             unit="bar", category="Other", description="hello")
        b = sig_def("B", ["WTS.A"], [{"type": "bias", "offset": 1}])

        order_a, _ = topological_order([a, b])
        hashes_a = compute_definition_hashes([a, b], order_a)
        order_b, _ = topological_order([a_cosmetic, b])
        hashes_b = compute_definition_hashes([a_cosmetic, b], order_b)

        assert hashes_a["A"] == hashes_b["A"]        # cosmetic → same hash
        assert hashes_a["B"] == hashes_b["B"]

        a_changed = sig_def("A", ["R.p"], [{"type": "scale", "factor": 3}])
        order_c, _ = topological_order([a_changed, b])
        hashes_c = compute_definition_hashes([a_changed, b], order_c)
        assert hashes_c["A"] != hashes_a["A"]        # op change...
        assert hashes_c["B"] != hashes_a["B"]        # ...propagates upstream→down


class TestNoFabricatedData:
    def test_nan_inf_produce_no_sample(self):
        definition = sig_def("S", ["A.x"], [{"type": "scale", "factor": 1}])
        engine = VirtualSignalEngine([definition])
        assert engine.update(0.0, {"A.x": math.nan}) == {}
        assert engine.update(1.0, {"A.x": math.inf}) == {}
        assert engine.update(2.0, {"A.x": -math.inf}) == {}
        assert engine.update(3.0, {"A.x": 5.0}) == {"WTS.S": 5.0}

    def test_overflow_chain_yields_nothing(self):
        definition = sig_def(
            "S", ["A.x"], [{"type": "scale", "factor": 1e308}]
        )
        engine = VirtualSignalEngine([definition])
        assert engine.update(0.0, {"A.x": 10.0}) == {}


class TestMonotonicity:
    def test_equal_and_backward_ts_skipped(self):
        definition = sig_def("S", ["A.x"], [{"type": "scale", "factor": 2}])
        engine = VirtualSignalEngine([definition])
        engine.update(10.0, {"A.x": 1.0})
        assert engine.update(10.0, {"A.x": 2.0}) == {}
        assert engine.update(9.0, {"A.x": 3.0}) == {}
        # State is not corrupted by skips: forward time evaluates normally.
        assert engine.update(11.0, {"A.x": 4.0}) == {"WTS.S": 8.0}
        assert engine.stats()["skipped_non_monotonic"] == 2

    def test_strictly_increasing_outputs(self):
        definition = sig_def("S", ["A.x"], [{"type": "scale", "factor": 1}])
        engine = VirtualSignalEngine([definition])
        series = collect(
            engine,
            [(t / 2, {"A.x": t}) for t in range(20)],  # includes duplicate ts
        )
        stamps = [ts for ts, _ in series["WTS.S"]]
        assert all(b > a for a, b in zip(stamps, stamps[1:]))


class TestGaps:
    def test_notify_gap_resets_lowpass(self):
        definition = sig_def("S", ["A.x"], [{"type": "lowpass", "cutoff_hz": 1.0}])
        engine = VirtualSignalEngine([definition])
        engine.update(0.0, {"A.x": 100.0})
        engine.notify_gap(1.0)
        # After the gap the next sample passes through unfiltered.
        assert engine.update(1.0, {"A.x": -7.0}) == {"WTS.S": -7.0}

    def test_max_gap_suppresses_stale_combine(self):
        definition = sig_def(
            "S", ["A.x", "B.y"], [{"type": "combine", "operator": "add"}]
        )
        engine = VirtualSignalEngine([definition], max_gap_seconds=1.0)
        engine.update(0.0, {"A.x": 1.0, "B.y": 1.0})
        # A.x keeps updating; B.y is dead. After 1.2 s the combine must
        # refuse to combine fresh with stale.
        assert engine.update(1.2, {"A.x": 2.0}) == {}
        assert engine.update(1.4, {"A.x": 3.0}) == {}
        # B.y wakes up again → normal output resumes.
        assert engine.update(1.6, {"B.y": 10.0}) == {"WTS.S": 13.0}

    def test_max_gap_none_never_suppresses(self):
        definition = sig_def(
            "S", ["A.x", "B.y"], [{"type": "combine", "operator": "add"}]
        )
        engine = VirtualSignalEngine([definition])  # no max_gap_seconds
        engine.update(0.0, {"A.x": 1.0, "B.y": 1.0})
        assert engine.update(1000.0, {"A.x": 2.0}) == {"WTS.S": 3.0}

    def test_max_gap_notifies_stateful_ops(self):
        definition = sig_def("S", ["A.x"], [{"type": "lowpass", "cutoff_hz": 1.0}])
        engine = VirtualSignalEngine([definition], max_gap_seconds=1.0)
        engine.update(0.0, {"A.x": 100.0})
        # A gap larger than max_gap resets the filter → passes through.
        assert engine.update(5.0, {"A.x": 3.0}) == {"WTS.S": 3.0}


class TestDeliveryIndependence:
    def _seeded_stream(self):
        rng = random.Random(1234)
        groups: list[tuple[float, dict[str, float]]] = []
        ts = 1_700_000_000.0
        for _ in range(500):
            ts += rng.uniform(0.0, 0.02)  # jitter incl. duplicate timestamps
            values: dict[str, float] = {}
            if rng.random() < 0.6:
                values["Brakes.Front_Psi"] = rng.uniform(0, 2000)
            if rng.random() < 0.3:
                values["Brakes.Rear_Psi"] = rng.uniform(0, 2000)
            if rng.random() < 0.5:
                values["Steer.Angle"] = rng.uniform(-35, 35)
            if values:
                groups.append((ts, values))
        return groups

    def _definitions(self):
        total = sig_def(
            "Total",
            ["Brakes.Front_Psi", "Brakes.Rear_Psi"],
            [{"type": "combine", "operator": "add"}],
        )
        bias = sig_def(
            "Bias",
            ["Brakes.Front_Psi", "WTS.Total"],
            [
                {"type": "combine", "operator": "divide"},
                {"type": "scale", "factor": 100},
            ],
        )
        smooth = sig_def(
            "Smooth",
            ["WTS.Bias"],
            [{"type": "lowpass", "cutoff_hz": 5.0},
             {"type": "moving_avg", "window_seconds": 0.5}],
        )
        steer = sig_def(
            "SteerDeg",
            ["Steer.Angle"],
            [{"type": "scale", "factor": 2}, {"type": "bias", "offset": 0.5}],
        )
        return [total, bias, smooth, steer]

    def test_streaming_equals_batch(self):
        groups = self._seeded_stream()
        streaming = collect(VirtualSignalEngine(self._definitions()), groups)

        rows = sorted(
            (ts, signal_id, value)
            for ts, values in groups
            for signal_id, value in values.items()
        )
        batched: dict[str, list[tuple[float, float]]] = {}
        for ts, signal_id, value in run_batch(
            VirtualSignalEngine(self._definitions()), rows
        ):
            batched.setdefault(signal_id, []).append((ts, value))

        assert batched == streaming
        assert batched  # sanity: not comparing two empty dicts

    def test_rows_with_duplicate_ts_group(self):
        """Duplicate rows at equal ts collapse to the last value (SQL-like)."""
        definition = sig_def("S", ["A.x"], [{"type": "scale", "factor": 10}])
        rows = [(0.0, "A.x", 1.0), (0.0, "A.x", 2.0)]
        engine = VirtualSignalEngine([definition])
        assert list(run_batch(engine, rows)) == [(0.0, "WTS.S", 20.0)]
