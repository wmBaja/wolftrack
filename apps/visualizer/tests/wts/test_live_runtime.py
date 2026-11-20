"""Unit tests for the live runtime clock logic (Part 4.1)."""
import math

import pytest

from wts.live import LiveWtsRuntime
from wts.schema import OperationDef, VirtualSignalDef


def scale(name, inputs, ops):
    return VirtualSignalDef(
        name=name,
        inputs=tuple(inputs),
        operations=tuple(
            OperationDef(o["type"], {k: v for k, v in o.items() if k != "type"})
            for o in ops
        ),
    )


def total_def():
    return scale("Total", ("A.x", "A.y"), [{"type": "combine", "operator": "add"}])


def avg_def():
    return scale("Avg", ("A.x",), [{"type": "moving_avg", "window_seconds": 1.0}])


def make(defs=None, **kw):
    return LiveWtsRuntime(defs if defs is not None else [total_def()], **kw)


class TestBasics:
    def test_raw_inputs_are_transitive(self):
        runtime = make([
            total_def(),
            scale("Twice", ("WTS.Total",), [{"type": "scale", "factor": 2}]),
        ])
        assert runtime.raw_inputs == frozenset({"A.x", "A.y"})

    def test_process_returns_outputs(self):
        runtime = make()
        outputs, step = runtime.process(1000.0, {"A.x": 1.0, "A.y": 2.0})
        assert outputs == {"WTS.Total": 3.0}
        assert step is False

    def test_missing_timestamp_skipped_and_counted(self):
        runtime = make()
        outputs, step = runtime.process(None, {"A.x": 1.0, "A.y": 2.0})
        assert outputs == {} and step is False
        assert runtime.stats()["missing_timestamps"] == 1
        # a real timestamp afterwards works normally
        outputs, _ = runtime.process(1000.0, {"A.x": 1.0, "A.y": 2.0})
        assert outputs == {"WTS.Total": 3.0}


class TestClockRules:
    def test_normal_in_order_samples(self):
        runtime = make()
        runtime.process(1000.0, {"A.x": 1.0, "A.y": 1.0})
        outputs, step = runtime.process(1000.1, {"A.x": 2.0, "A.y": 2.0})
        assert outputs == {"WTS.Total": 4.0} and step is False

    def test_backward_jitter_skipped_no_reset(self):
        runtime = make([avg_def()])
        runtime.process(1000.0, {"A.x": 10.0})
        runtime.process(1001.0, {"A.x": 20.0})
        # 50 ms backward jitter: skip the sample, keep all state.
        outputs, step = runtime.process(1000.95, {"A.x": 999.0})
        assert outputs == {} and step is False
        # state intact: the skipped sample left no trace; the 20@1001 sample
        # is still in the 1 s window (the 10@1000 one aged out normally)
        outputs, _ = runtime.process(1001.5, {"A.x": 30.0})
        assert math.isclose(outputs["WTS.Avg"], 25.0)  # (20+30)/2

    def test_backward_clock_step_resets_and_flags(self):
        runtime = make([avg_def()])
        runtime.process(1000.0, {"A.x": 10.0})
        runtime.process(1001.0, {"A.x": 20.0})
        # 3 s earlier than last: clock step (e.g. DAQ reboot / looped replay)
        outputs, step = runtime.process(998.0, {"A.x": 5.0})
        assert step is True
        assert outputs == {"WTS.Avg": 5.0}  # resumed immediately on new base
        assert runtime.stats()["clock_steps"] == 1
        # old history is gone: next average uses only post-step samples
        outputs, _ = runtime.process(998.5, {"A.x": 7.0})
        assert math.isclose(outputs["WTS.Avg"], 6.0)

    def test_forward_jump_is_gap_not_reset(self):
        runtime = make([avg_def()])
        runtime.process(1000.0, {"A.x": 10.0})
        outputs, step = runtime.process(1030.0, {"A.x": 20.0})
        assert step is False  # forward jump never sets clock_step
        assert outputs == {"WTS.Avg": 20.0}  # old sample aged out by gap

    def test_note_dropped_clears_stateful(self):
        runtime = make([avg_def()])
        runtime.process(1000.0, {"A.x": 10.0})
        runtime.note_dropped(1000.1)
        outputs, _ = runtime.process(1000.1, {"A.x": 20.0})
        assert outputs == {"WTS.Avg": 20.0}

    def test_note_dropped_none_ts_ignored(self):
        runtime = make()
        runtime.note_dropped(None)  # no crash

    def test_reset_clears_last_ts(self):
        runtime = make([avg_def()])
        runtime.process(1000.0, {"A.x": 10.0})
        runtime.reset()
        # after reset, an "old" timestamp is treated as a fresh base, not
        # as a backward step
        outputs, step = runtime.process(900.0, {"A.x": 3.0})
        assert step is False
        assert outputs == {"WTS.Avg": 3.0}


class TestVersion:
    def test_version_recorded(self):
        assert make(version=7).version == 7

    def test_empty_defs_still_constructs(self):
        runtime = LiveWtsRuntime([])
        assert runtime.raw_inputs == frozenset()
        assert runtime.process(1.0, {"A.x": 1.0}) == ({}, False)
