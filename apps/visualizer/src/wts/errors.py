"""Errors shared by the WTS package."""
from __future__ import annotations

from typing import Iterable, Mapping


class WtsValidationError(ValueError):
    """Raised when one or more virtual-signal definitions are invalid.

    Carries **all** errors found in a single pass, each as a mapping with
    ``code``, ``signal``, and ``message`` keys.
    """

    def __init__(self, errors: Iterable[Mapping[str, str]]) -> None:
        self.errors: list[dict[str, str]] = [dict(error) for error in errors]
        summary = "; ".join(
            f"{error.get('signal', '?')}: {error.get('message', '')}"
            for error in self.errors
        )
        super().__init__(summary or "invalid virtual signal definitions")


class OpError(ValueError):
    """An operation was constructed with invalid parameters."""
