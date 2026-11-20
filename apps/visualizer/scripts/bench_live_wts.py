"""Live virtual-signal throughput benchmark (Part 4.5, not a CI gate).

Simulates the hot part of the live loop: N frames/s through a
LiveWtsRuntime with M definitions, measuring per-frame processing time
(the same call that runs synchronously inside the asyncio loop).

Target (initial, adjust after measuring on target hardware): 5,000
frames/s x 30 definitions with p99 per-frame time under ~1 ms (the loop
budget is 50 ms per flush => 250 frames per 50 ms window => ~0.2 ms/frame
at target; measure what you get).

Run:  uv run python scripts/bench_live_wts.py [frames] [defs]
"""
from __future__ import annotations

import statistics
import sys
import time

sys.path.insert(0, "src")

from wts.live import LiveWtsRuntime  # noqa: E402
from wts.schema import OperationDef, VirtualSignalDef  # noqa: E402


def build_definitions(count: int) -> list[VirtualSignalDef]:
    raw_inputs = ["Brakes.Front_Psi", "Brakes.Rear_Psi", "Steering.Angle"]
    defs: list[VirtualSignalDef] = []
    # Two seed definitions off raw signals
    defs.append(VirtualSignalDef(
        name="Total",
        inputs=("Brakes.Front_Psi", "Brakes.Rear_Psi"),
        operations=(OperationDef("combine", {"operator": "add"}),),
    ))
    defs.append(VirtualSignalDef(
        name="Yaw",
        inputs=("Steering.Angle",),
        operations=(
            OperationDef("scale", {"factor": 0.5}),
            OperationDef("bias", {"offset": 1.0}),
        ),
    ))
    # The rest chain off previous virtual signals with a filter op each
    for index in range(count - 2):
        base = defs[index % 2].name
        defs.append(VirtualSignalDef(
            name=f"Chain_{index}",
            inputs=(f"WTS.{base}", "Brakes.Front_Psi"),
            operations=(
                OperationDef("combine", {"operator": "add"}),
                OperationDef("lowpass", {"cutoff_hz": 5.0}),
            ),
        ))
    return defs


def main() -> None:
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    defs_count = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    defs = build_definitions(defs_count)
    runtime = LiveWtsRuntime(defs, version=1, max_gap_seconds=1.0)
    subscribed = {d.signal_id for d in defs}

    times: list[float] = []
    ts = 1_000_000.0
    dt = 1.0 / 5000.0
    for index in range(frames):
        values = {
            "Brakes.Front_Psi": (index % 2000) * 1.0,
            "Brakes.Rear_Psi": (index % 1500) * 1.0,
            "Steering.Angle": (index % 820) - 410.0,
        }
        start = time.perf_counter()
        outputs, _ = runtime.process(ts, values)
        # the loop's emit cost (dict appends for subscribed ids)
        for wts_id, value in outputs.items():
            if wts_id in subscribed:
                _ = (ts, value)
        times.append(time.perf_counter() - start)
        ts += dt

    times_ms = [t * 1000 for t in times]
    total = sum(times)
    times_ms.sort()
    p50 = times_ms[len(times_ms) // 2]
    p99 = times_ms[int(len(times_ms) * 0.99)]
    print(f"definitions : {len(defs)} (raw inputs: {len(runtime.raw_inputs)})")
    print(f"frames      : {frames:,} at 5000 f/s simulated")
    print(f"total       : {total:.3f} s  "
          f"({frames / total:,.0f} frames/s of pure Python headroom)")
    print(f"per-frame   : p50 {p50:.3f} ms   p99 {p99:.3f} ms")
    print(f"50 ms window budget: {0.05 / (total / frames):.0f} frames")


if __name__ == "__main__":
    main()
