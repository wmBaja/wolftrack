"""The built-in head operation: combine every input of a definition."""
from __future__ import annotations

from typing import Sequence

from wts.ops import register
from wts.ops.base import HeadOp, ParamSpec


@register
class CombineOp(HeadOp):
    """Arithmetic across all inputs, in input order.

    ``subtract`` folds ``a - b - c ...`` and ``divide`` requires exactly two
    inputs; dividing by zero emits *no sample* (never 0 or inf).
    """

    type = "combine"
    label = "Combine signals"
    arity = (1, None)
    params = (
        ParamSpec(
            name="operator",
            type="enum",
            choices=("add", "subtract", "multiply", "divide"),
            default="add",
            required=True,
            help="How to combine the inputs (order matters for subtract/divide).",
        ),
    )

    def check_arity(self, input_count: int) -> None:
        if self.operator == "divide" and input_count != 2:
            from wts.errors import OpError

            raise OpError(
                f"combine/divide needs exactly 2 inputs, got {input_count}"
            )
        if input_count < 1:
            from wts.errors import OpError

            raise OpError("combine needs at least 1 input")

    def apply_vector(
        self, ts: float, values: Sequence[float], stamps: Sequence[float]
    ) -> float | None:
        if self.operator == "add":
            return sum(values)
        if self.operator == "subtract":
            result = values[0]
            for value in values[1:]:
                result -= value
            return result
        if self.operator == "multiply":
            product = 1.0
            for value in values:
                product *= value
            return product
        # divide
        if values[1] == 0.0:
            return None
        return values[0] / values[1]

    def to_json(self) -> dict[str, object]:
        return {"operator": self.operator}
