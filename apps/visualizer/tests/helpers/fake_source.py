"""A scripted :class:`~pipeline.source.DataSource` emitting ``can_batch``.

Frames are encoded against the synthetic DBC (``make_blf.synthetic_database``)
so ``PipelineManager._run_loop`` decodes them exactly like a DAQ stream.
Each item yielded is one ZMQ-shaped message:

    {"type": "can_batch", "frames": [...], "dropped_batches": n}

Frame dicts carry ``arbitration_id``, ``data`` and ``timestamp``; a frame
built with ``timestamp=None`` omits the key entirely, to exercise the
missing-timestamp rule.
"""
from __future__ import annotations

from typing import Iterable, Sequence

import cantools

from pipeline.source import DataSource

from tests.helpers.make_blf import synthetic_database


def encode_frame_dict(
    timestamp: float | None,
    message_name: str,
    values: dict[str, float],
    db: cantools.database.Database | None = None,
) -> dict:
    db = db or synthetic_database()
    message = db.get_message_by_name(message_name)
    frame: dict = {
        "arbitration_id": message.frame_id,
        "data": list(db.encode_message(message_name, values)),
    }
    if timestamp is not None:
        frame["timestamp"] = timestamp
    return frame


class FakeDataSource(DataSource):
    """Yield scripted frames in batches, then finish (optionally stay open).

    ``batches``: sequence of ``(frames, dropped_batches)`` where ``frames``
    is a sequence of ``(timestamp, message_name, {signal: value})`` tuples.
    ``hold_open`` keeps ``stream()`` alive after the script so tests can
    mutate state mid-session and then stop the pipeline explicitly.
    """

    def __init__(
        self,
        batches: Sequence[tuple[Iterable[tuple], int]],
        hold_open: bool = False,
        db: cantools.database.Database | None = None,
    ) -> None:
        self.db = db or synthetic_database()
        self.messages = [
            {
                "type": "can_batch",
                "frames": [
                    encode_frame_dict(ts, name, values, self.db)
                    for ts, name, values in frames
                ],
                "dropped_batches": dropped,
            }
            for frames, dropped in batches
        ]
        self.hold_open = hold_open
        self.connected = False
        self.disconnects = 0
        # Signal used by tests to release a hold-open stream.
        import asyncio

        self._gate: asyncio.Event | None = None

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.disconnects += 1
        if self._gate is not None:
            self._gate.set()

    async def stream(self):
        import asyncio

        for message in self.messages:
            yield message
        if self.hold_open:
            self._gate = asyncio.Event()
            await self._gate.wait()
