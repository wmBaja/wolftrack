"""Single-value arithmetic operations: scale, bias."""
from __future__ import annotations

from wts.errors import OpError
from wts.ops import register
from wts.ops.base import Op, ParamSpec


@register
class ScaleOp(Op):
    """Multiply every sample by a constant factor."""

    type = "scale"
    label = "Scale"
    params = (
        ParamSpec(
            name="factor",
            type="float",
            required=True,
            help="Multiply the signal by this number.",
        ),
    )

    def apply(self, ts: float, value: float) -> float | None:
        return value * self.factor


@register
class BiasOp(Op):
    """Add a constant offset to every sample."""

    type = "bias"
    label = "Bias"
    params = (
        ParamSpec(
            name="offset",
            type="float",
            required=True,
            help="Add this number to the signal.",
        ),
    )

    def apply(self, ts: float, value: float) -> float | None:
        return value + self.offset
