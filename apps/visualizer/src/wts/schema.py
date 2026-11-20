"""Virtual-signal definition parsing, validation, and hashing.

Pure: no I/O, no wall clock. See ``docs/wts/00-architecture.md`` §3-§4.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from wts.errors import OpError, WtsValidationError

#: ``WTS.<name>`` id prefix for virtual signals (D12).
WTS_PREFIX = "WTS."

NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")

MAX_SIGNALS = 200
MAX_OPERATIONS = 16
MAX_DEPTH = 16


def canonical_json(value: Any) -> str:
    """Stable JSON text used as hashing input.

    ``sort_keys`` orders object keys; ``allow_nan=False`` rejects NaN/inf so
    a corrupt definition can never silently hash.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      default=_encode, allow_nan=False)


def _encode(value: Any) -> Any:
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    raise TypeError(f"unencodable value: {type(value).__name__}")


@dataclass(frozen=True)
class OperationDef:
    """One operation in a chain: ``type`` plus raw parameters."""

    type: str
    params: dict[str, Any] = field(default_factory=dict, hash=False)

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": self.type}
        payload.update(self.params)
        return payload

    @classmethod
    def from_json(cls, data: Any) -> "OperationDef":
        if not isinstance(data, dict):
            raise WtsValidationError(
                [{"code": "op_invalid", "signal": "", "message":
                  f"operation must be an object, got {type(data).__name__}"}]
            )
        op_type = data.get("type")
        if not isinstance(op_type, str) or not op_type:
            raise WtsValidationError(
                [{"code": "op_invalid", "signal": "",
                  "message": "operation is missing a string 'type'"}]
            )
        params = {key: value for key, value in data.items() if key != "type"}
        return cls(type=op_type, params=params)


@dataclass(frozen=True)
class VirtualSignalDef:
    """A parsed, structurally valid virtual-signal definition."""

    name: str
    kind: str = "continuous"
    category: str = "Custom"
    unit: str = ""
    description: str = ""
    inputs: tuple[str, ...] = ()
    operations: tuple[OperationDef, ...] = ()

    @property
    def signal_id(self) -> str:
        return f"{WTS_PREFIX}{self.name}"

    def to_json(self) -> dict[str, Any]:
        """Full definition as stored in a ``.wts`` file."""
        payload: dict[str, Any] = {
            "name": self.name,
            "kind": self.kind,
            "category": self.category,
            "unit": self.unit,
        }
        if self.description:
            payload["description"] = self.description
        payload["inputs"] = list(self.inputs)
        payload["operations"] = [op.to_json() for op in self.operations]
        return payload

    def compute_json(self) -> dict[str, Any]:
        """Compute-affecting subset (D8): excludes unit/category/description."""
        return {
            "kind": self.kind,
            "inputs": list(self.inputs),
            "operations": [op.to_json() for op in self.operations],
        }

    @classmethod
    def from_json(cls, data: Any, *, index: int = 0) -> "VirtualSignalDef":
        """Parse with structural validation.

        Raises :class:`WtsValidationError` carrying every field error found.
        Cross-definition checks (cycles, unknown inputs) live in
        :mod:`wts.graph` / :func:`wts.schema.validate_definitions`.
        """
        errors: list[dict[str, str]] = []
        if not isinstance(data, dict):
            raise WtsValidationError(
                [{"code": "definition_invalid", "signal": f"#{index}",
                  "message": "definition must be an object"}]
            )
        name = data.get("name")
        signal_label = name if isinstance(name, str) else f"#{index}"
        if not isinstance(name, str) or not NAME_PATTERN.match(name):
            errors.append({
                "code": "name_invalid",
                "signal": signal_label,
                "message": "name must match ^[A-Za-z_][A-Za-z0-9_]{0,63}$",
            })
            name = signal_label

        kind = data.get("kind", "continuous")
        if kind != "continuous":
            errors.append({
                "code": "kind_unsupported",
                "signal": str(name),
                "message": f"kind {kind!r} is not supported yet; only "
                           f"'continuous' is available",
            })

        raw_inputs = data.get("inputs")
        inputs: tuple[str, ...] = ()
        if not isinstance(raw_inputs, list) or not raw_inputs:
            errors.append({
                "code": "inputs_missing",
                "signal": str(name),
                "message": "inputs must be a non-empty list of signal ids",
            })
        elif not all(isinstance(item, str) and item for item in raw_inputs):
            errors.append({
                "code": "inputs_invalid",
                "signal": str(name),
                "message": "every input must be a non-empty string",
            })
        else:
            inputs = tuple(raw_inputs)

        raw_ops = data.get("operations")
        operations: tuple[OperationDef, ...] = ()
        if not isinstance(raw_ops, list) or not raw_ops:
            errors.append({
                "code": "operations_missing",
                "signal": str(name),
                "message": "operations must be a non-empty list",
            })
        elif len(raw_ops) > MAX_OPERATIONS:
            errors.append({
                "code": "operations_too_many",
                "signal": str(name),
                "message": f"at most {MAX_OPERATIONS} operations are allowed",
            })
        else:
            ops: list[OperationDef] = []
            for op_data in raw_ops:
                try:
                    ops.append(OperationDef.from_json(op_data))
                except WtsValidationError as error:
                    for item in error.errors:
                        item["signal"] = str(name)
                    errors.extend(error.errors)
            operations = tuple(ops)

        if errors:
            raise WtsValidationError(errors)

        description = data.get("description", "")
        if description is None:
            description = ""
        if not isinstance(description, str):
            raise WtsValidationError(
                [{"code": "description_invalid", "signal": str(name),
                  "message": "description must be a string"}]
            )

        return cls(
            name=str(name),
            kind="continuous",
            category=_string_or_default(data.get("category", "Custom"), "Custom"),
            unit=_string_or_default(data.get("unit", ""), ""),
            description=description,
            inputs=inputs,
            operations=operations,
        )


def _string_or_default(value: Any, default: str) -> str:
    return value if isinstance(value, str) and value.strip() else default


def definition_hash_base(definition: VirtualSignalDef) -> str:
    """SHA-256 of the compute-affecting JSON of one definition.

    Upstream ``def_hash`` values must be mixed in by the caller via
    :func:`wts.graph.compute_definition_hashes`; on its own this is only the
    definition's own contribution.
    """
    return hashlib.sha256(
        canonical_json(definition.compute_json()).encode("utf-8")
    ).hexdigest()


def parse_definitions(payload: Any) -> list[VirtualSignalDef]:
    """Parse a list of definition JSON objects; one error object for all."""
    if not isinstance(payload, list):
        raise WtsValidationError(
            [{"code": "signals_invalid", "signal": "",
              "message": "'signals' must be a list"}]
        )
    if len(payload) > MAX_SIGNALS:
        raise WtsValidationError(
            [{"code": "signals_too_many", "signal": "",
              "message": f"at most {MAX_SIGNALS} virtual signals are allowed"}]
        )
    errors: list[dict[str, str]] = []
    defs: list[VirtualSignalDef] = []
    seen: set[str] = set()
    for index, item in enumerate(payload):
        try:
            definition = VirtualSignalDef.from_json(item, index=index)
        except WtsValidationError as error:
            errors.extend(error.errors)
            continue
        if definition.name in seen:
            errors.append({
                "code": "name_duplicate",
                "signal": definition.name,
                "message": "duplicate virtual signal name",
            })
            continue
        seen.add(definition.name)
        defs.append(definition)
    if errors:
        raise WtsValidationError(errors)
    return defs


def op_param_errors(
    definition: VirtualSignalDef, registry: dict[str, type]
) -> list[dict[str, str]]:
    """Validate op types/params and head/chain positions for one definition."""
    from wts.ops.base import HeadOp

    errors: list[dict[str, str]] = []
    for position, op_def in enumerate(definition.operations):
        op_cls = registry.get(op_def.type)
        if op_cls is None:
            errors.append({
                "code": "op_unknown",
                "signal": definition.name,
                "message": f"unknown operation type '{op_def.type}'",
            })
            continue
        try:
            instance = op_cls(**op_def.params)
        except OpError as error:
            errors.append({
                "code": "op_params",
                "signal": definition.name,
                "message": f"operation '{op_def.type}': {error}",
            })
            continue
        is_head = position == 0
        if getattr(op_cls, "is_head", False) and not is_head:
            errors.append({
                "code": "op_not_head_position",
                "signal": definition.name,
                "message": f"operation '{op_def.type}' is a head operation and "
                           "must be first in the chain",
            })
        if not getattr(op_cls, "is_head", False) and is_head and len(
            definition.inputs
        ) > 1:
            errors.append({
                "code": "op_head_required",
                "signal": definition.name,
                "message": "with multiple inputs the first operation must be "
                           "a head operation (e.g. combine)",
            })
        if isinstance(instance, HeadOp):
            try:
                instance.check_arity(len(definition.inputs))
            except OpError as error:
                errors.append({
                    "code": "op_arity",
                    "signal": definition.name,
                    "message": str(error),
                })
    return errors
