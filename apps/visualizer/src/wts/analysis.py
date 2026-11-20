"""Cross-check a WTS file against the DBC: valid vs broken definitions.

A definition is **broken** (kept in the file, excluded from computation,
flagged in the UI) when an input id is unknown, an op type is unknown, an op
has invalid parameters, or it depends on a broken definition. Hard structural
problems (cycles, depth, duplicate names) are returned as *hard errors* so an
API write can reject them; a file that merely loads with them keeps loading
with everything affected marked broken (docs/wts §3).
"""
from __future__ import annotations

from typing import Any

from wts import ops as ops_module
from wts.errors import OpError, WtsValidationError
from wts.graph import topological_order, wts_dependencies
from wts.schema import VirtualSignalDef, op_param_errors


class AnalysisResult:
    """Outcome of validating a set of definitions against a DBC."""

    def __init__(self) -> None:
        self.valid: list[VirtualSignalDef] = []
        #: signal name -> human reason
        self.broken: dict[str, str] = {}
        #: issues incl. severity ("error" | "warning"), for API/UI display
        self.issues: list[dict[str, str]] = []
        #: structural errors that reject an API write (cycles, depth, …)
        self.hard_errors: list[dict[str, str]] = []


def analyze(
    definitions: list[VirtualSignalDef],
    dbc_signal_ids: set[str] | None,
    raw_broken: dict[str, str] | None = None,
) -> AnalysisResult:
    """Classify definitions. ``dbc_signal_ids=None`` skips raw-id checking
    (e.g. when no DBC loaded — nothing raw can be trusted)."""
    result = AnalysisResult()
    broken: dict[str, str] = dict(raw_broken or {})
    for name, reason in (raw_broken or {}).items():
        result.issues.append({
            "code": "definition_invalid",
            "signal": name,
            "severity": "error",
            "message": reason,
        })

    candidates = [
        definition for definition in definitions
        if definition.name not in broken
    ]

    # Per-definition local problems (unknown op, bad params, arity, head pos).
    for definition in candidates:
        errors = op_param_errors(definition, ops_module.OPS)
        if errors:
            broken[definition.name] = "; ".join(item["message"] for item in errors)
            result.issues.extend(
                {**item, "severity": "error"} for item in errors
            )
    candidates = [
        definition for definition in candidates if definition.name not in broken
    ]

    # Unknown inputs (raw ids vs DBC; WTS ids vs the definition set).
    names = {definition.name for definition in definitions}
    for definition in list(candidates):
        for item in definition.inputs:
            if item.startswith("WTS."):
                dep = item[len("WTS."):]
                if dep not in names:
                    broken[definition.name] = (
                        f"input '{item}' is not a defined virtual signal"
                    )
                    result.issues.append({
                        "code": "input_unknown",
                        "signal": definition.name,
                        "severity": "error",
                        "message": f"input '{item}' is not a defined virtual signal",
                    })
                    break
            elif dbc_signal_ids is not None and item not in dbc_signal_ids:
                broken[definition.name] = (
                    f"input '{item}' is not in the active DBC"
                )
                result.issues.append({
                    "code": "input_unknown",
                    "signal": definition.name,
                    "severity": "error",
                    "message": f"input '{item}' is not in the active DBC",
                })
                break
    candidates = [
        definition for definition in candidates if definition.name not in broken
    ]

    # Structural graph errors: hard errors (reject writes) and the affected
    # definitions become broken so the file still opens.
    order, graph_errors = topological_order(candidates)
    if graph_errors:
        result.hard_errors.extend(graph_errors)
        for error in graph_errors:
            affected = error.get("signal") or ""
            if affected:
                broken[affected] = error["message"]
                result.issues.append({**error, "severity": "error"})
        candidates = [
            definition for definition in candidates
            if definition.name not in broken
        ]
        order, residual = topological_order(candidates)
        result.hard_errors.extend(residual)

    # Cascade: anything depending on a broken definition is broken too.
    changed = True
    while changed:
        changed = False
        for definition in list(candidates):
            if definition.name in broken:
                continue
            for item in definition.inputs:
                dep = item[len("WTS."):] if item.startswith("WTS.") else None
                if dep is not None and dep in broken:
                    broken[definition.name] = (
                        f"depends on broken {item}"
                    )
                    result.issues.append({
                        "code": "input_broken",
                        "signal": definition.name,
                        "severity": "error",
                        "message": f"depends on broken {item}",
                    })
                    changed = True
                    break
        candidates = [
            definition for definition in candidates
            if definition.name not in broken
        ]

    result.valid = candidates
    result.broken = broken
    return result


def check_definition_write(
    definition: VirtualSignalDef,
    siblings: list[VirtualSignalDef],
    dbc_signal_ids: set[str] | None,
    raw_broken: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Validate a single definition as if stored alongside ``siblings``.

    Returns the list of issues for this definition; empty means acceptable.
    Used by ``PUT /api/wts/signals/{name}`` before writing anything.
    ``raw_broken`` maps names that exist in the file but are already broken,
    so references to them resolve (and cascade as broken) instead of looking
    like unknown ids.
    """
    combined = [
        item for item in siblings if item.name != definition.name
    ] + [definition]
    sibling_broken = {
        name: reason
        for name, reason in (raw_broken or {}).items()
        if name != definition.name
    }
    result = analyze(combined, dbc_signal_ids, raw_broken=sibling_broken)
    own = [
        issue for issue in result.issues
        if issue.get("signal") == definition.name
    ]
    hard = [
        error for error in result.hard_errors
        if error.get("signal") == definition.name
        or definition.name in (error.get("message") or "")
    ]
    return own + [{**error, "severity": "error"} for error in hard]
