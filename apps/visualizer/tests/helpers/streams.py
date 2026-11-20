"""Seeded deterministic sample generators for tests."""
from __future__ import annotations

import math
import random
from typing import Iterator


def sine(rate: float, amplitude: float = 1.0, frequency: float = 1.0, phase: float = 0.0):
    """Return a generator yielding (dt, value) at a fixed rate starting at t=0."""
    index = 0
    while True:
        dt = index / rate
        yield dt, amplitude * math.sin(2.0 * math.pi * frequency * dt + phase)
        index += 1


def ramp(rate: float, slope: float = 1.0):
    """Ramp value = slope * t at a fixed sample rate."""
    index = 0
    while True:
        dt = index / rate
        yield dt, slope * dt
        index += 1


def step(rate: float, low: float = 0.0, high: float = 1.0, step_time: float = 1.0):
    """Step function: ``low`` before ``step_time``, then ``high``."""
    index = 0
    while True:
        dt = index / rate
        yield dt, high if dt >= step_time else low
        index += 1


def noise(rate: float, amplitude: float = 1.0, seed: int = 0):
    """Uniform noise in [-amplitude, amplitude] at a fixed rate, seeded."""
    rng = random.Random(seed)
    index = 0
    while True:
        dt = index / rate
        yield dt, rng.uniform(-amplitude, amplitude)
        index += 1


def jittered(stream: Iterator[tuple[float, float]], max_jitter: float, seed: int = 0):
    """Add seeded jitter to timestamps of a (dt, value) stream, keeping order.

    Timestamps remain non-decreasing (jitter is clamped to the previous ts) so
    the stream stays valid for the engine's monotonic rule. Duplicate
    timestamps can occur on purpose.
    """
    rng = random.Random(seed)
    previous: float | None = None
    for dt, value in stream:
        ts = dt + rng.uniform(-max_jitter, max_jitter)
        if previous is not None and ts < previous:
            ts = previous
        previous = ts
        yield ts, value
