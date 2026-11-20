"""Build synthetic DBC text and .blf log files for tests.

The synthetic DBC models a two-signal message (so two decoded signals share
one frame timestamp, exercising same-timestamp grouping) plus a single-signal
message.
"""
from __future__ import annotations

import struct
from typing import Iterable, Sequence

import can
import cantools

# Frame ids chosen to avoid CAN extended-id concerns in tests.
BRAKES_FRAME_ID = 0x100
STEERING_FRAME_ID = 0x110

SYNTHETIC_DBC = """VERSION ""

NS_ :

BS_:

BU_: ECU

BO_ 256 Brakes: 8 ECU
 SG_ Front_Psi : 0|16@1+ (0.25,0) [0|16383.75] "psi" Vector__XXX
 SG_ Rear_Psi : 16|16@1+ (0.25,0) [0|16383.75] "psi" Vector__XXX

BO_ 272 Steering: 8 ECU
 SG_ Angle : 0|16@1+ (1,-2000) [0|65535] "deg" Vector__XXX

"""


def synthetic_database():
    """Return the synthetic DBC parsed as a cantools database."""
    return cantools.database.load_string(SYNTHETIC_DBC, database_format="dbc")


def encode_frame(
    timestamp: float, message_name: str, values: dict[str, float]
) -> can.Message:
    """Encode one CAN frame from signal values."""
    db = synthetic_database()
    data = db.encode_message(message_name, values)
    return can.Message(
        timestamp=timestamp,
        arbitration_id=db.get_message_by_name(message_name).frame_id,
        data=data,
        is_extended_id=False,
    )


def make_blf(
    path: str,
    frames: Iterable[tuple[float, str, dict[str, float]]],
) -> str:
    """Write a .blf file from (timestamp, message_name, {signal: value}) tuples."""
    with can.BLFWriter(path) as writer:
        for timestamp, message_name, values in frames:
            writer.on_message_received(encode_frame(timestamp, message_name, values))
    return path


def frames_from_series(
    times: Sequence[float],
    brake_front: Sequence[float],
    brake_rear: Sequence[float],
    steering: Sequence[float] | None = None,
) -> list[tuple[float, str, dict[str, float]]]:
    """Interleave Brakes (two signals per frame) and optional Steering frames."""
    frames: list[tuple[float, str, dict[str, float]]] = []
    for index, ts in enumerate(times):
        frames.append(
            (ts, "Brakes", {"Front_Psi": brake_front[index], "Rear_Psi": brake_rear[index]})
        )
        if steering is not None:
            frames.append((ts, "Steering", {"Angle": steering[index]}))
    return frames
