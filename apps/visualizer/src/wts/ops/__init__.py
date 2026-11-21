"""Operation registry.

Registering a class with :func:`register` is the only step needed to add an
operation (D15). ``GET /api/wts/operations`` serves :func:`describe_all`.

PyInstaller note: the explicit submodule imports at the bottom of this module
ensure the op modules are bundled and their ``@register`` decorators run at
import time under static analysis. They must stay *after* ``register`` is
defined (the op modules import ``register`` from this package).
"""
from __future__ import annotations

from typing import Any, Type

from wts.ops.base import HeadOp, Op, ParamSpec

OPS: dict[str, Type[Op]] = {}


def register(op_cls: Type[Op]) -> Type[Op]:
    """Class decorator: add an operation class to the global registry."""
    op_type = getattr(op_cls, "type", None)
    if not op_type:
        raise ValueError(f"{op_cls!r} has no 'type'")
    existing = OPS.get(op_type)
    if existing is not None and existing is not op_cls:
        raise ValueError(f"operation type '{op_type}' already registered")
    OPS[op_type] = op_cls
    return op_cls


def unregister(op_type: str) -> None:
    """Remove an op (tests only)."""
    OPS.pop(op_type, None)


def create(op_type: str, params: dict[str, Any]) -> Op:
    """Instantiate a registered op with validated parameters.

    Raises :class:`KeyError` for unknown types and :class:`wts.errors.OpError`
    for bad parameters.
    """
    op_cls = OPS[op_type]
    return op_cls(**params)


def describe_all() -> dict[str, Any]:
    """JSON-serializable operation catalog (D15)."""
    operations = []
    for op_type in sorted(OPS):
        op_cls = OPS[op_type]
        entry: dict[str, Any] = {
            "type": op_type,
            "label": op_cls.label,
            "is_head": bool(op_cls.is_head),
            "params": [spec.to_json() for spec in op_cls.params],
        }
        if isinstance(op_cls, type) and issubclass(op_cls, HeadOp):
            entry["min_inputs"] = op_cls.arity[0]
            entry["max_inputs"] = op_cls.arity[1]
        operations.append(entry)
    catalog: dict[str, Any] = {"operations": operations}
    combine_cls = OPS.get("combine")
    if combine_cls is not None:
        for spec in combine_cls.params:
            if spec.name == "operator" and spec.choices:
                catalog["combine_operators"] = list(spec.choices)
    return catalog


# Explicit imports so PyInstaller bundles the modules and @register runs.
from wts.ops import basic, combine, expr, filters  # noqa: E402,F401

__all__ = [
    "OPS",
    "Op",
    "HeadOp",
    "ParamSpec",
    "register",
    "unregister",
    "create",
    "describe_all",
]
