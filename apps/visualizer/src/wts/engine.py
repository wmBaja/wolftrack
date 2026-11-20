"""The pure virtual-signal engine (docs/wts/00-architecture.md §4).

``VirtualSignalEngine`` turns timestamped input updates into virtual-signal
samples. It performs no I/O, reads no wall clock, and produces deterministic
output for an identical sequence of updates (I1, I2).
"""
from __future__ import annotations

import math
from typing import Iterable, Mapping

from wts import ops as ops_module
from wts.errors import WtsValidationError
from wts.graph import (
    compute_definition_hashes,
    required_raw_inputs,
    topological_order,
)
from wts.schema import (
    NAME_PATTERN,
    WTS_PREFIX,
    VirtualSignalDef,
    op_param_errors,
)


class _Processor:
    """Per-definition evaluation state."""

    __slots__ = (
        "definition",
        "signal_id",
        "inputs",
        "head",
        "chain",
        "last_output_ts",
        "last_eval_ts",
    )

    def __init__(
        self,
        definition: VirtualSignalDef,
        head,
        chain: list,
    ) -> None:
        self.definition = definition
        self.signal_id = definition.signal_id
        self.inputs = definition.inputs
        self.head = head
        self.chain = chain
        self.last_output_ts: float | None = None
        self.last_eval_ts: float | None = None

    def reset(self) -> None:
        for op in self._all_ops():
            op.reset()
        self.last_output_ts = None
        self.last_eval_ts = None

    def notify_gap(self, ts: float) -> None:
        for op in self._all_ops():
            op.notify_gap(ts)

    def _all_ops(self) -> Iterable:
        if self.head is not None:
            yield self.head
        yield from self.chain


class VirtualSignalEngine:
    """Evaluate virtual-signal definitions over timestamped updates.

    ``update(ts, values)`` processes every sample that shares one timestamp
    (one CAN frame) exactly once (D6). Outputs are keyed ``WTS.<name>``.
    """

    def __init__(
        self,
        definitions: list[VirtualSignalDef],
        max_gap_seconds: float | None = None,
    ) -> None:
        errors: list[dict[str, str]] = []
        names = {definition.name for definition in definitions}
        if len(names) != len(definitions):
            errors.append({
                "code": "name_duplicate",
                "signal": "",
                "message": "duplicate virtual signal name",
            })
        for definition in definitions:
            if definition.kind != "continuous":
                errors.append({
                    "code": "kind_unsupported",
                    "signal": definition.name,
                    "message": f"kind {definition.kind!r} is not supported "
                               "yet; only 'continuous' is available",
                })
            if not NAME_PATTERN.match(definition.name):
                errors.append({
                    "code": "name_invalid",
                    "signal": definition.name,
                    "message": "name must match ^[A-Za-z_][A-Za-z0-9_]{0,63}$",
                })
            if not definition.inputs:
                errors.append({
                    "code": "inputs_missing",
                    "signal": definition.name,
                    "message": "inputs must be a non-empty list",
                })
            for item in definition.inputs:
                if item.startswith(WTS_PREFIX) and item[len(WTS_PREFIX):] not in names:
                    errors.append({
                        "code": "input_unknown",
                        "signal": definition.name,
                        "message": f"input '{item}' is not a defined virtual "
                                   "signal in this engine",
                    })
            errors.extend(op_param_errors(definition, ops_module.OPS))
        if errors:
            raise WtsValidationError(errors)

        order, graph_errors = topological_order(definitions)
        if graph_errors:
            raise WtsValidationError(graph_errors)

        self.max_gap_seconds = max_gap_seconds
        self._definitions: dict[str, VirtualSignalDef] = {
            definition.name: definition for definition in definitions
        }
        self._order = order
        self.definition_hashes = compute_definition_hashes(definitions, order)

        # Held latest value/timestamp per input id (raw) and output id (WTS).
        self._values: dict[str, float] = {}
        self._stamps: dict[str, float] = {}

        self._processors: list[_Processor] = []
        for name in order:
            definition = self._definitions[name]
            head = None
            chain_start = 0
            first = definition.operations[0]
            first_cls = ops_module.OPS.get(first.type)
            if first_cls is not None and first_cls.is_head:
                head = ops_module.create(first.type, first.params)
                chain_start = 1
            chain = [
                ops_module.create(op.type, op.params)
                for op in definition.operations[chain_start:]
            ]
            self._processors.append(_Processor(definition, head, chain))
        self._by_id: dict[str, _Processor] = {
            processor.signal_id: processor for processor in self._processors
        }

        self._counters = {"skipped_non_monotonic": 0, "none_results": 0}

    # ------------------------------------------------------------------ API

    def required_inputs(
        self, wanted_ids: list[str] | None = None
    ) -> set[str]:
        """Raw signal ids needed (transitively) to compute ``wanted_ids``."""
        return required_raw_inputs(list(self._definitions.values()), wanted_ids)

    def update(
        self, ts: float, values: Mapping[str, float]
    ) -> dict[str, float]:
        """Evaluate one timestamped update; returns outputs keyed by WTS id.

        ``values`` must map raw signal ids to numbers; it is never retained
        after the call.
        """
        if not self._processors:
            return {}

        changed: set[str] = set()
        for signal_id, value in values.items():
            self._values[signal_id] = value
            self._stamps[signal_id] = ts
            changed.add(signal_id)

        outputs: dict[str, float] = {}
        for processor in self._processors:
            result = self._evaluate(processor, ts, changed)
            if result is None:
                continue
            outputs[processor.signal_id] = result
            changed.add(processor.signal_id)
        return outputs

    def notify_gap(self, ts: float) -> None:
        """Tell every processor to discard previous-sample state."""
        for processor in self._processors:
            processor.notify_gap(ts)

    def reset(self) -> None:
        """Clear all held values and processor state."""
        self._values.clear()
        self._stamps.clear()
        for processor in self._processors:
            processor.reset()

    def stats(self) -> dict[str, int]:
        """Engine counters for callers to log (the engine never logs)."""
        return dict(self._counters)

    # ----------------------------------------------------------- internals

    def _evaluate(
        self, processor: _Processor, ts: float, changed: set[str]
    ) -> float | None:
        inputs = processor.inputs

        # (a) at least one input changed in this update,
        if not any(item in changed for item in inputs):
            return None
        # (b) every input has been seen at least once.
        stamps = []
        for item in inputs:
            stamp = self._stamps.get(item)
            if stamp is None or item not in self._values:
                return None
            stamps.append(stamp)

        # Strictly increasing output timestamps per signal (I8).
        if (
            processor.last_output_ts is not None
            and ts <= processor.last_output_ts
        ):
            self._counters["skipped_non_monotonic"] += 1
            return None

        if self.max_gap_seconds is not None:
            # 1. own evaluation gap clears stateful ops.
            if (
                processor.last_eval_ts is not None
                and ts - processor.last_eval_ts > self.max_gap_seconds
            ):
                processor.notify_gap(ts)
            # 2. stale held input: never combine dead data with fresh.
            if len(inputs) > 1 and ts - min(stamps) > self.max_gap_seconds:
                processor.notify_gap(ts)
                self._counters["none_results"] += 1
                return None

        processor.last_eval_ts = ts
        result = self._run_chain(processor, ts, stamps)
        if result is None or (isinstance(result, float) and not math.isfinite(result)):
            self._counters["none_results"] += 1
            return None

        processor.last_output_ts = ts
        self._values[processor.signal_id] = result
        self._stamps[processor.signal_id] = ts
        return result

    def _run_chain(
        self, processor: _Processor, ts: float, stamps: list[float]
    ) -> float | None:
        inputs = processor.inputs
        if processor.head is not None:
            values = [self._values[item] for item in inputs]
            result = processor.head.apply_vector(ts, values, stamps)
        else:
            result = self._values[inputs[0]]
        if result is None:
            return None
        for op in processor.chain:
            result = op.apply(ts, result)
            if result is None:
                return None
        return result
