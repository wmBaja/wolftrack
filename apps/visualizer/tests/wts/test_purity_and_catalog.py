"""Purity (I2), catalog contract, and the head-op extension point."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from tests.wts.helpers import collect, sig_def
from wts.batch import run_batch
from wts.engine import VirtualSignalEngine
from wts.ops import OPS, describe_all, register, unregister
from wts.ops.base import HeadOp, Op, ParamSpec
from wts.schema import canonical_json

WTS_SOURCE = Path(__file__).resolve().parents[2] / "src" / "wts"

FORBIDDEN = [
    "time.time",
    "datetime.now",
    "datetime.today",
    "random",
    "open(",
    "sqlite3",
    "asyncio",
    "os.",
    "requests",
    "socket",
    "eval(",
    "exec(",
    "pickle",
]


#: The pure engine core. wts_file.py (parse/format handling of file bytes is
#: its job) and live.py (clock state, still no I/O/wall clock) are exempt.
PURITY_EXEMPT = {"wts_file.py", "live.py"}


class TestPurity:
    @pytest.mark.parametrize(
        "path",
        [
            p
            for p in sorted(WTS_SOURCE.rglob("*.py"))
            if p.name not in PURITY_EXEMPT
        ],
        ids=lambda p: str(p.relative_to(WTS_SOURCE)),
    )
    def test_engine_sources_stay_pure(self, path: Path):
        source = path.read_text(encoding="utf-8")
        # Strip comments/docstrings coarsely: check code lines only.
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""'):
                continue
            for token in FORBIDDEN:
                if token in stripped:
                    raise AssertionError(
                        f"{path.name} violates purity: {token!r} in "
                        f"{stripped!r}"
                    )


class TestCanonicalJson:
    def test_stable_and_sorted(self):
        a = canonical_json({"b": 1, "a": [1, {"d": 2, "c": 3}]})
        b = canonical_json({"a": [1, {"c": 3, "d": 2}], "b": 1})
        assert a == b
        assert canonical_json(1.5) == "1.5"

    def test_rejects_non_finite(self):
        with pytest.raises(ValueError):
            canonical_json(math.nan)


class TestHeadOpExtension:
    """A plugin-style stateful 3-input HeadOp works end to end (D15 groundwork)."""

    def setup_method(self):
        @register
        class TripleSum(HeadOp):
            type = "test_triple_sum"
            label = "Triple sum"
            arity = (3, 3)
            params = (ParamSpec(name="gain", type="float", default=1.0),)

            def reset(self) -> None:
                self._last_total: float | None = None

            def notify_gap(self, ts: float) -> None:
                self._last_total = None

            def apply_vector(self, ts, values, stamps):
                assert len(values) == 3
                # Stamps must be per-input last-update timestamps.
                self._last_total = sum(values) * self.gain
                # Record the newest stamp gap so tests can inspect staleness.
                self._newest_gap = ts - max(stamps)
                return self._last_total

        self.triple = TripleSum

    def teardown_method(self):
        unregister("test_triple_sum")

    def test_registered_in_catalog(self):
        catalog = describe_all()
        json.dumps(catalog)
        entry = next(
            op for op in catalog["operations"] if op["type"] == "test_triple_sum"
        )
        assert entry["is_head"] is True
        assert entry["min_inputs"] == 3 and entry["max_inputs"] == 3

    def test_engine_and_batch_end_to_end(self):
        definition = sig_def(
            "T",
            ["A.x", "B.y", "C.z"],
            [{"type": "test_triple_sum", "gain": 2.0}],
        )
        groups = [
            (0.0, {"A.x": 1.0, "B.y": 2.0, "C.z": 3.0}),
            (1.0, {"A.x": 4.0}),                       # held inputs
            (2.0, {"B.y": 5.0, "C.z": 6.0}),
        ]
        streaming = collect(VirtualSignalEngine([definition]), groups)
        # (1+2+3)*2 = 12; (4+2+3)*2 = 18; (4+5+6)*2 = 30
        assert streaming == {"WTS.T": [(0.0, 12.0), (1.0, 18.0), (2.0, 30.0)]}

        rows = [
            (ts, sig, value)
            for ts, values in groups
            for sig, value in values.items()
        ]
        rows.sort()
        batched = list(run_batch(VirtualSignalEngine([definition]), rows))
        assert batched == [(ts, "WTS.T", value) for ts, value in streaming["WTS.T"]]

    def test_stamps_reflect_update_times(self):
        definition = sig_def(
            "T", ["A.x", "B.y", "C.z"], [{"type": "test_triple_sum"}]
        )
        engine = VirtualSignalEngine([definition])
        engine.update(0.0, {"A.x": 1.0, "B.y": 1.0, "C.z": 1.0})
        engine.update(10.0, {"A.x": 2.0})
        processor = engine._processors[0]
        assert processor.head._newest_gap == 0.0     # A.x arrived this update
        assert processor.head._last_total == 4.0

    def test_arity_enforced(self):
        bad = sig_def("T", ["A.x", "B.y"], [{"type": "test_triple_sum"}])
        from wts.errors import WtsValidationError

        with pytest.raises(WtsValidationError) as excinfo:
            VirtualSignalEngine([bad])
        assert excinfo.value.errors[0]["code"] == "op_arity"
