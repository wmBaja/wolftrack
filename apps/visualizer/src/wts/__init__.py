"""WolfTrack Signals (WTS): user-defined virtual signals.

Pure, mode-agnostic signal processing for both ``.blf`` log analysis and live
DAQ streaming. See ``docs/wts/00-architecture.md`` for the binding semantics.
"""
from wts.engine import VirtualSignalEngine
from wts.batch import run_batch
from wts.errors import WtsValidationError
from wts.schema import OperationDef, VirtualSignalDef, definition_hash_base

__all__ = [
    "VirtualSignalEngine",
    "run_batch",
    "WtsValidationError",
    "OperationDef",
    "VirtualSignalDef",
    "definition_hash_base",
]
