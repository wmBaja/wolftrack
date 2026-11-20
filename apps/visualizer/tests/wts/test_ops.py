"""Unit tests for the five built-in operations (hand-computed values)."""
from __future__ import annotations

import math

import pytest

from tests.wts.helpers import sig_def
from wts.engine import VirtualSignalEngine
from wts.errors import OpError, WtsValidationError
from wts.ops import OPS, describe_all, register, unregister
from wts.ops.base import HeadOp, Op, ParamSpec
from wts.ops.basic import BiasOp, ScaleOp
from wts.ops.combine import CombineOp
from wts.ops.filters import LowpassOp, MovingAvgOp


def run_chain(op, samples):
    return [op.apply(ts, value) for ts, value in samples]


class TestScaleBias:
    def test_scale(self):
        op = ScaleOp(factor=2.5)
        # 10 * 2.5 = 25; -4 * 2.5 = -10
        assert run_chain(op, [(0, 10.0), (1, -4.0)]) == [25.0, -10.0]

    def test_bias(self):
        op = BiasOp(offset=-3.0)
        # 10 - 3 = 7; 0 - 3 = -3
        assert run_chain(op, [(0, 10.0), (1, 0.0)]) == [7.0, -3.0]

    def test_missing_required_param(self):
        with pytest.raises(OpError):
            ScaleOp()

    def test_unknown_param(self):
        with pytest.raises(OpError):
            ScaleOp(factor=1, extra=2)

    def test_param_out_of_range(self):
        with pytest.raises(OpError):
            MovingAvgOp(window_seconds=0)
        with pytest.raises(OpError):
            MovingAvgOp(window_seconds=601)


class TestCombine:
    def test_add(self):
        op = CombineOp(operator="add")
        # 1 + 2 + 3 = 6
        assert op.apply_vector(0, [1.0, 2.0, 3.0], [0, 0, 0]) == 6.0

    def test_subtract_left_fold(self):
        op = CombineOp(operator="subtract")
        # 10 - 3 - 2 = 5
        assert op.apply_vector(0, [10.0, 3.0, 2.0], [0, 0, 0]) == 5.0

    def test_multiply(self):
        op = CombineOp(operator="multiply")
        assert op.apply_vector(0, [2.0, -3.0, 4.0], [0, 0, 0]) == -24.0

    def test_divide(self):
        op = CombineOp(operator="divide")
        assert op.apply_vector(0, [10.0, 4.0], [0, 0]) == 2.5

    def test_divide_by_zero_emits_nothing(self):
        op = CombineOp(operator="divide")
        assert op.apply_vector(0, [10.0, 0.0], [0, 0]) is None

    def test_divide_arity_rejected_at_engine_level(self):
        bad1 = sig_def("One", ["A.x"], [{"type": "combine", "operator": "divide"}])
        bad3 = sig_def(
            "Three",
            ["A.x", "A.y", "A.z"],
            [{"type": "combine", "operator": "divide"}],
        )
        with pytest.raises(WtsValidationError) as excinfo:
            VirtualSignalEngine([bad1, bad3])
        codes = {error["code"] for error in excinfo.value.errors}
        assert "op_arity" in codes
        signals = {error["signal"] for error in excinfo.value.errors}
        assert signals == {"One", "Three"}

    def test_invalid_operator(self):
        with pytest.raises(OpError):
            CombineOp(operator="pow")


class TestMovingAvg:
    def test_time_window(self):
        op = MovingAvgOp(window_seconds=1.0)
        # Window is (ts - w, ts]: the sample exactly w seconds old drops out.
        result = run_chain(
            op, [(0.0, 10.0), (1.0, 4.0), (1.5, 2.0), (2.0, 6.0)]
        )
        assert result[0] == 10.0            # emits from the first sample
        assert result[1] == 4.0             # 10.0 dropped at t=1.0
        assert result[2] == pytest.approx((4 + 2) / 2)
        assert result[3] == pytest.approx(4.0)   # avg(2, 6)

    def test_notify_gap_clears_window(self):
        op = MovingAvgOp(window_seconds=100.0)
        run_chain(op, [(0.0, 10.0), (1.0, 20.0)])
        op.notify_gap(2.0)
        # After the gap only the new sample remains: avg(99) = 99.
        assert op.apply(2.0, 99.0) == 99.0

    def test_running_sum_renormalized_as_window_drains(self):
        # Feed tiny values then a single big value; the running sum must be
        # exactly the big value (drift-free) once the window holds one sample.
        op = MovingAvgOp(window_seconds=1.0)
        for index in range(50):
            ts = index * 0.01
            op.apply(ts, 1e-9 * (index % 3))
        value = op.apply(100.0, 5.0)
        assert value == pytest.approx(5.0, abs=1e-12)
        assert value == 5.0  # exact after renorm with a single-sample window

    def test_running_sum_renormalized_on_interval(self):
        op = MovingAvgOp(window_seconds=600.0)
        for index in range(10_001):
            op.apply(float(index), 1e-9 if index % 7 else 1.0)
        value = op.apply(10_001.0, 3.0)
        # The renorm at update 10_000 keeps the running sum drift-free.
        window = op._window
        assert value == pytest.approx(
            sum(item[1] for item in window) / len(window), abs=1e-9
        )


class TestLowpass:
    def test_first_sample_passes_through(self):
        op = LowpassOp(cutoff_hz=1.0)
        assert op.apply(0.0, 42.0) == 42.0

    def test_rc_alpha(self):
        op = LowpassOp(cutoff_hz=1.0)
        op.apply(0.0, 0.0)
        rc = 1.0 / (2.0 * math.pi)  # ≈ 0.1591549
        dt = 0.1
        alpha = dt / (rc + dt)
        expected = 0.0 + alpha * (10.0 - 0.0)
        assert op.apply(dt, 10.0) == pytest.approx(expected)

    def test_non_positive_dt_skipped(self):
        op = LowpassOp(cutoff_hz=1.0)
        op.apply(5.0, 1.0)
        assert op.apply(5.0, 2.0) is None
        assert op.apply(4.0, 2.0) is None

    def test_notify_gap_passes_next_sample(self):
        op = LowpassOp(cutoff_hz=1.0)
        op.apply(0.0, 100.0)
        op.notify_gap(10.0)
        assert op.apply(10.0, -5.0) == -5.0


class TestEngineBasics:
    def test_scale_chain(self):
        definition = sig_def(
            "S", ["A.x"], [{"type": "scale", "factor": 2}, {"type": "bias", "offset": 1}]
        )
        engine = VirtualSignalEngine([definition])
        # (7 * 2) + 1 = 15
        assert engine.update(0.0, {"A.x": 7.0}) == {"WTS.S": 15.0}

    def test_stats_counters(self):
        definition = sig_def(
            "D", ["A.x", "A.y"], [{"type": "combine", "operator": "divide"}]
        )
        engine = VirtualSignalEngine([definition])
        engine.update(0.0, {"A.x": 1.0, "A.y": 1.0})   # emits at ts 0
        engine.update(0.0, {"A.x": 2.0, "A.y": 1.0})   # non-monotonic (same ts)
        engine.update(1.0, {"A.x": 2.0, "A.y": 0.0})   # divide by zero
        stats = engine.stats()
        assert stats["none_results"] == 1
        assert stats["skipped_non_monotonic"] == 1

    def test_required_inputs(self):
        a = sig_def("A", ["R.p"], [{"type": "scale", "factor": 1}])
        b = sig_def("B", ["WTS.A", "R.q"], [{"type": "combine", "operator": "add"}])
        c = sig_def("C", ["R.z"], [{"type": "bias", "offset": 1}])
        engine = VirtualSignalEngine([a, b, c])
        assert engine.required_inputs() == {"R.p", "R.q", "R.z"}
        assert engine.required_inputs(["WTS.B"]) == {"R.p", "R.q"}

    def test_engine_rejects_unknown_op(self):
        bad = sig_def("X", ["A.x"], [{"type": "nope"}])
        with pytest.raises(WtsValidationError) as excinfo:
            VirtualSignalEngine([bad])
        assert excinfo.value.errors[0]["code"] == "op_unknown"

    def test_head_op_must_be_first(self):
        bad = sig_def("X", ["A.x"], [{"type": "scale", "factor": 2}, {"type": "combine", "operator": "add"}])
        with pytest.raises(WtsValidationError) as excinfo:
            VirtualSignalEngine([bad])
        assert excinfo.value.errors[0]["code"] == "op_not_head_position"

    def test_multi_input_requires_head(self):
        bad = sig_def("X", ["A.x", "A.y"], [{"type": "scale", "factor": 2}])
        with pytest.raises(WtsValidationError) as excinfo:
            VirtualSignalEngine([bad])
        assert excinfo.value.errors[0]["code"] == "op_head_required"

    def test_kind_must_be_continuous(self):
        bad = sig_def("X", ["A.x"], [{"type": "scale", "factor": 2}], kind="event")
        with pytest.raises(WtsValidationError):
            VirtualSignalEngine([bad])


class TestCatalog:
    def test_describe_all_shape(self):
        catalog = describe_all()
        assert catalog["combine_operators"] == ["add", "subtract", "multiply", "divide"]
        types = {op["type"] for op in catalog["operations"]}
        assert types >= {"combine", "scale", "bias", "moving_avg", "lowpass"}
        import json

        json.dumps(catalog)  # must be serializable
        for op in catalog["operations"]:
            assert op["label"]
            assert isinstance(op["is_head"], bool)
            for param in op["params"]:
                assert param["name"] and param["type"]
        heads = {op["type"] for op in catalog["operations"] if op["is_head"]}
        assert heads == {"combine"}

    def test_dummy_registration_appears(self):
        @register
        class DummyOp(Op):
            type = "dummy_test"
            label = "Dummy"
            params = (ParamSpec(name="amount", type="float", default=1.0),)

            def apply(self, ts, value):
                return value + self.amount

        try:
            catalog = describe_all()
            entry = next(
                op for op in catalog["operations"] if op["type"] == "dummy_test"
            )
            assert entry["is_head"] is False
            assert entry["params"][0]["name"] == "amount"
            definition = sig_def("D", ["A.x"], [{"type": "dummy_test", "amount": 5}])
            engine = VirtualSignalEngine([definition])
            assert engine.update(0.0, {"A.x": 1.0}) == {"WTS.D": 6.0}
        finally:
            unregister("dummy_test")
