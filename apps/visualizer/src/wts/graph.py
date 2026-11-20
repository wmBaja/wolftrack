"""Dependency resolution over virtual-signal definitions (D5).

Pure helpers: topological order, cycle reporting as a path, depth limit,
subgraph selection, and definition hashes (upstream-aware, D8).
"""
from __future__ import annotations

import hashlib

from wts.errors import WtsValidationError
from wts.schema import MAX_DEPTH, WTS_PREFIX, VirtualSignalDef, definition_hash_base


def wts_dependencies(definition: VirtualSignalDef) -> list[str]:
    """Names of the ``WTS.*`` inputs of one definition."""
    return [
        item[len(WTS_PREFIX):]
        for item in definition.inputs
        if item.startswith(WTS_PREFIX)
    ]


def build_indexes(
    defs: list[VirtualSignalDef],
) -> dict[str, VirtualSignalDef]:
    return {definition.name: definition for definition in defs}


def topological_order(
    defs: list[VirtualSignalDef],
) -> tuple[list[str], list[dict[str, str]]]:
    """Return (evaluation order, errors).

    Orders definitions so that every definition comes after the ``WTS.*``
    definitions it depends on. A cycle is reported once with its path;
    definitions deeper than ``MAX_DEPTH`` are reported per definition.
    """
    by_name = build_indexes(defs)
    errors: list[dict[str, str]] = []
    order: list[str] = []
    on_stack: list[str] = []       # current DFS path
    cycle_paths: set[tuple[str, ...]] = set()
    depth: dict[str, int] = {}     # also marks "finished"

    def visit(name: str) -> int:
        if name in on_stack:
            path = on_stack[on_stack.index(name):] + [name]
            key = tuple(path)
            if key not in cycle_paths:
                cycle_paths.add(key)
                errors.append({
                    "code": "dependency_cycle",
                    "signal": path[0],
                    "message": "dependency cycle: " + " -> ".join(
                        f"{WTS_PREFIX}{item}" for item in path
                    ),
                })
            return 0
        if name in depth:
            return depth[name]
        definition = by_name[name]
        on_stack.append(name)
        best = 0
        for dep in wts_dependencies(definition):
            if dep in by_name:
                best = max(best, visit(dep) + 1)
        on_stack.pop()
        if best + 1 > MAX_DEPTH:
            errors.append({
                "code": "dependency_depth",
                "signal": name,
                "message": f"dependency depth exceeds the limit of {MAX_DEPTH}",
            })
        depth[name] = best
        order.append(name)
        return best

    for definition in defs:
        visit(definition.name)
    return order, errors


def compute_definition_hashes(
    defs: list[VirtualSignalDef], order: list[str]
) -> dict[str, str]:
    """def_hash per definition: own compute hash + every upstream hash (D8)."""
    by_name = build_indexes(defs)
    hashes: dict[str, str] = {}
    for name in order:
        definition = by_name[name]
        parts = [definition_hash_base(definition)]
        for dep in sorted(wts_dependencies(definition)):
            if dep in hashes:
                parts.append(hashes[dep])
        hashes[name] = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return hashes


def dependents_of(defs: list[VirtualSignalDef], name: str) -> list[str]:
    """Direct WTS dependents of one definition."""
    return [
        definition.name
        for definition in defs
        if name in wts_dependencies(definition) and definition.name != name
    ]


def transitive_dependents(defs: list[VirtualSignalDef], name: str) -> list[str]:
    """Everything that (transitively) consumes ``WTS.name``."""
    found: list[str] = []
    frontier = [name]
    seen = {name}
    while frontier:
        current = frontier.pop()
        for dependent in dependents_of(defs, current):
            if dependent not in seen:
                seen.add(dependent)
                found.append(dependent)
                frontier.append(dependent)
    return found


def transitive_wts_ancestors(
    defs: list[VirtualSignalDef], names: list[str]
) -> set[str]:
    """Every WTS definition that ``names`` (transitively) depend on."""
    by_name = build_indexes(defs)
    ancestors: set[str] = set()
    frontier = list(names)
    while frontier:
        current = frontier.pop()
        definition = by_name.get(current)
        if definition is None:
            continue
        for dep in wts_dependencies(definition):
            if dep not in ancestors and dep in by_name:
                ancestors.add(dep)
                frontier.append(dep)
    return ancestors


def subgraph_defs(
    defs: list[VirtualSignalDef], wanted_ids: list[str]
) -> list[VirtualSignalDef]:
    """Subset of ``defs`` = wanted ids + transitive WTS ancestors.

    ``wanted_ids`` may be given as bare names or ``WTS.*`` ids. Returned in
    the input's declared order (construction re-validates and re-orders).
    """
    wanted = {
        item[len(WTS_PREFIX):] if item.startswith(WTS_PREFIX) else item
        for item in wanted_ids
    }
    keep = wanted | transitive_wts_ancestors(defs, list(wanted))
    return [definition for definition in defs if definition.name in keep]


def required_raw_inputs(
    defs: list[VirtualSignalDef], wanted_ids: list[str] | None = None
) -> set[str]:
    """Raw (non-``WTS``) ids needed transitively to compute ``wanted_ids``."""
    if wanted_ids is None:
        subgraph = defs
    else:
        subgraph = subgraph_defs(defs, wanted_ids)
    raw: set[str] = set()
    for definition in subgraph:
        for item in definition.inputs:
            if not item.startswith(WTS_PREFIX):
                raw.add(item)
    return raw


def validate_graph(
    defs: list[VirtualSignalDef], known_ids: set[str] | None = None
) -> tuple[list[VirtualSignalDef], list[dict[str, str]], list[str], dict[str, str]]:
    """Full cross-definition validation.

    Returns ``(order_ok?, ...)`` — precisely: (topological order, hard errors,
    issues). Hard errors (cycles, depth) raise for API writes; the caller
    decides. ``known_ids`` are valid raw signal ids; inputs not found there
    (and not a defined WTS signal) are reported in issues, not hard errors:
    a file with such a definition still opens with the definition marked
    broken.
    """
    order, hard_errors = topological_order(defs)
    if hard_errors:
        raise WtsValidationError(hard_errors)
    hashes = compute_definition_hashes(defs, order)
    issues: list[dict[str, str]] = []
    names = set(hashes)
    for definition in defs:
        for item in definition.inputs:
            if item.startswith(WTS_PREFIX):
                if item[len(WTS_PREFIX):] not in names:
                    issues.append({
                        "code": "input_unknown",
                        "signal": definition.name,
                        "severity": "error",
                        "message": f"input '{item}' is not a defined virtual signal",
                    })
            elif known_ids is not None and item not in known_ids:
                issues.append({
                    "code": "input_unknown",
                    "signal": definition.name,
                    "severity": "error",
                    "message": f"input '{item}' is not in the active DBC",
                })
    return [build_indexes(defs)[name] for name in order], issues, order, hashes
