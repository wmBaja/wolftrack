"""Shared helpers for WTS engine tests."""
from __future__ import annotations

from typing import Sequence

from wts.schema import OperationDef, VirtualSignalDef


def sig_def(
    name: str,
    inputs: Sequence[str],
    operations: Sequence[dict],
    **fields,
) -> VirtualSignalDef:
    """Build a VirtualSignalDef from plain dicts."""
    return VirtualSignalDef(
        name=name,
        inputs=tuple(inputs),
        operations=tuple(
            OperationDef(type=op["type"], params={k: v for k, v in op.items() if k != "type"})
            for op in operations
        ),
        **fields,
    )


def collect(engine, updates: Sequence[tuple[float, dict[str, float]]]):
    """Feed (ts, values) updates; return (signal_id -> [(ts, value), ...])."""
    series: dict[str, list[tuple[float, float]]] = {}
    for ts, values in updates:
        for signal_id, value in engine.update(ts, values).items():
            series.setdefault(signal_id, []).append((ts, value))
    return series
