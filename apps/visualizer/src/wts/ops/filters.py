"""Time-based filters: moving average and first-order low-pass.

Both are causal and use only sample timestamps (seconds), so live and log
paths agree at any sample rate.
"""
from __future__ import annotations

import math
from collections import deque

from wts.ops import register
from wts.ops.base import Op, ParamSpec

#: moving_avg window bound (seconds), deliberate (Part 1 gotcha).
_MAX_WINDOW_SECONDS = 600.0
#: Renormalize the running sum this often to kill float drift.
_RENORM_INTERVAL = 10_000


@register
class MovingAvgOp(Op):
    """Mean of samples inside ``ts - window_seconds < t <= ts``."""

    type = "moving_avg"
    label = "Moving average"
    params = (
        ParamSpec(
            name="window_seconds",
            type="float",
            required=True,
            min=1e-9,
            max=_MAX_WINDOW_SECONDS,
            unit="s",
            help="Width of the averaging window in seconds.",
        ),
    )

    def reset(self) -> None:
        self._window: deque[tuple[float, float]] = deque()
        self._sum = 0.0
        self._updates_since_renorm = 0

    def notify_gap(self, ts: float) -> None:
        self._window.clear()
        self._sum = 0.0
        self._updates_since_renorm = 0

    def apply(self, ts: float, value: float) -> float | None:
        self._window.append((ts, value))
        self._sum += value
        cutoff = ts - self.window_seconds
        while self._window and self._window[0][0] <= cutoff:
            self._sum -= self._window.popleft()[1]
        self._updates_since_renorm += 1
        if self._updates_since_renorm >= _RENORM_INTERVAL or len(self._window) <= 1:
            self._sum = sum(item[1] for item in self._window)
            self._updates_since_renorm = 0
        return self._sum / len(self._window)


@register
class LowpassOp(Op):
    """First-order RC low-pass: alpha = dt / (rc + dt), rc = 1/(2*pi*f)."""

    type = "lowpass"
    label = "Low-pass filter"
    params = (
        ParamSpec(
            name="cutoff_hz",
            type="float",
            required=True,
            min=1e-9,
            max=1e9,
            unit="Hz",
            help="Cutoff frequency of the filter in hertz.",
        ),
    )

    def reset(self) -> None:
        self._previous: float | None = None
        self._last_ts: float | None = None

    def notify_gap(self, ts: float) -> None:
        # Next sample passes through unfiltered.
        self._previous = None
        self._last_ts = None

    def apply(self, ts: float, value: float) -> float | None:
        if self._previous is None or self._last_ts is None:
            self._previous = value
            self._last_ts = ts
            return value
        dt = ts - self._last_ts
        if dt <= 0:
            return None
        rc = 1.0 / (2.0 * math.pi * self.cutoff_hz)
        alpha = dt / (rc + dt)
        self._previous = self._previous + alpha * (value - self._previous)
        self._last_ts = ts
        return self._previous
