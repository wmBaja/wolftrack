"""Operation base classes and the types that make the registry self-describing.

Every operation is a small, typed, parameterized class registered with
``@register`` in ``wts.ops``. ``Op`` subclasses process one value at a time;
``HeadOp`` subclasses are the only operations that may appear first in a chain
and receive the latest value of every input of the definition.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Literal, Sequence

from wts.errors import OpError

ParamType = Literal["float", "int", "string", "enum", "bool"]


@dataclass(frozen=True)
class ParamSpec:
    """Self-describing parameter, rendered by the dashboard editor (D15)."""

    name: str
    type: ParamType
    default: Any = None
    required: bool = False
    min: float | None = None
    max: float | None = None
    choices: tuple[str, ...] | None = None
    unit: str | None = None
    help: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "default": self.default,
            "required": self.required,
            "min": self.min,
            "max": self.max,
            "choices": list(self.choices) if self.choices is not None else None,
            "unit": self.unit,
            "help": self.help,
        }

    def validate(self, value: Any) -> Any:
        """Coerce/validate one parameter value against this spec."""
        if self.type == "float":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise OpError(f"parameter '{self.name}' must be a number")
            value = float(value)
        elif self.type == "int":
            if isinstance(value, bool):
                raise OpError(f"parameter '{self.name}' must be an integer")
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            if not isinstance(value, int):
                raise OpError(f"parameter '{self.name}' must be an integer")
        elif self.type == "bool":
            if not isinstance(value, bool):
                raise OpError(f"parameter '{self.name}' must be a boolean")
        elif self.type == "enum":
            if self.choices is None or value not in self.choices:
                choices = list(self.choices) if self.choices else []
                raise OpError(
                    f"parameter '{self.name}' must be one of {choices}"
                )
        elif self.type == "string":
            if not isinstance(value, str):
                raise OpError(f"parameter '{self.name}' must be a string")
        if self.type in ("float", "int"):
            if self.min is not None and value < self.min:
                raise OpError(f"parameter '{self.name}' must be >= {self.min}")
            if self.max is not None and value > self.max:
                raise OpError(f"parameter '{self.name}' must be <= {self.max}")
        return value


class Op(ABC):
    """Single-value chain operation."""

    type: ClassVar[str]
    label: ClassVar[str]
    is_head: ClassVar[bool] = False
    params: ClassVar[tuple[ParamSpec, ...]] = ()

    def __init__(self, **params: Any) -> None:
        spec_names = {spec.name for spec in self.params}
        unknown = set(params) - spec_names
        if unknown:
            raise OpError(
                f"operation '{self.type}' got unexpected parameter(s): "
                f"{sorted(unknown)}"
            )
        for spec in self.params:
            raw = params.get(spec.name)
            if raw is None:
                if spec.required:
                    raise OpError(
                        f"operation '{self.type}' requires parameter "
                        f"'{spec.name}'"
                    )
                setattr(self, spec.name, spec.default)
            else:
                setattr(self, spec.name, spec.validate(raw))
        self.reset()

    # -- state hooks (stateless ops do nothing) -------------------------
    def reset(self) -> None:
        """Discard internal state (engine rebuild / live reset)."""

    def notify_gap(self, ts: float) -> None:
        """React to a data gap (discard previous-sample state)."""

    @abstractmethod
    def apply(self, ts: float, value: float) -> float | None:
        """Transform one sample; ``None`` stops the chain for this update."""

    def to_json(self) -> dict[str, Any]:
        """Normalized parameter dict (defaults included) for hashing/serializing."""
        payload: dict[str, Any] = {}
        for spec in self.params:
            payload[spec.name] = getattr(self, spec.name, spec.default)
        return payload


class HeadOp(Op):
    """Multi-input first stage of a chain. Only valid as the first operation."""

    is_head: ClassVar[bool] = True
    #: (min_inputs, max_inputs or None)
    arity: ClassVar[tuple[int, int | None]] = (1, None)

    @abstractmethod
    def apply_vector(
        self, ts: float, values: Sequence[float], stamps: Sequence[float]
    ) -> float | None:
        """Combine every input's latest value; ``None`` stops the chain."""

    def apply(self, ts: float, value: float) -> float | None:
        raise OpError(f"operation '{self.type}' is a head operation")

    def check_arity(self, input_count: int) -> None:
        low, high = self.arity
        if input_count < low or (high is not None and input_count > high):
            high_label = "many" if high is None else str(high)
            raise OpError(
                f"operation '{self.type}' needs {low}..{high_label} inputs, "
                f"got {input_count}"
            )
