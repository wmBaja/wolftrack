"""The ``expr`` head operation: safe user-defined arithmetic over inputs."""
from __future__ import annotations

import math

import pytest

from tests.wts.helpers import collect, sig_def
from wts.batch import run_batch
from wts.engine import VirtualSignalEngine
from wts.errors import OpError, WtsValidationError
from wts.ops import OPS
from wts.ops.expr import ExprOp, compile_expression, evaluate_expression


def build(expression: str, inputs=("A.x", "A.y")) -> ExprOp:
    return ExprOp(expression=expression)


class TestEvaluator:
    def test_ratio_placeholder_order(self):
        series = collect(
            VirtualSignalEngine(
                [sig_def("R", ["A.x", "A.y"], [{"type": "expr", "expression": "%s / %s"}])]
            ),
            [
                (0.0, {"A.x": 400.0, "A.y": 200.0}),
                (1.0, {"A.x": 100.0, "A.y": 400.0}),
            ],
        )
        assert series["WTS.R"] == [(0.0, 2.0), (1.0, 0.25)]

    def test_single_signal_offset(self):
        op = build("%s - 300", inputs=("A.x",))
        assert op.apply_vector(0.0, [500.0], [0.0]) == 200.0

    def test_precedence_and_parens(self):
        assert build("%s + 2 * %s").apply_vector(0, [1.0, 3.0], [0, 0]) == 7.0
        assert build("(-%s) ** 2").apply_vector(0, [3.0], [0]) == 9.0

    def test_modulo_coexists_with_placeholders(self):
        assert build("%s % 10", inputs=("A.x",)).apply_vector(0, [25.0], [0]) == 5.0
        assert build("%s % %s").apply_vector(0, [7.0, 4.0], [0, 0]) == 3.0

    def test_functions_and_constants(self):
        assert build("sqrt(%s)", inputs=("A.x",)).apply_vector(0, [9.0], [0]) == 3.0
        assert build("abs(%s)", inputs=("A.x",)).apply_vector(0, [-4.0], [0]) == 4.0
        assert build("min(%s, %s)").apply_vector(0, [3.0, 1.0], [0, 0]) == 1.0
        got = build("pi * %s", inputs=("A.x",)).apply_vector(0, [2.0], [0])
        assert got == pytest.approx(2 * math.pi)

    def test_fewer_placeholders_than_inputs_ok(self):
        # Unreferenced second input still gates emission.
        definition = sig_def(
            "One", ["A.x", "A.y"], [{"type": "expr", "expression": "%s * 2"}]
        )
        engine = VirtualSignalEngine([definition])
        assert engine.update(0.0, {"A.x": 5.0}) == {}
        assert engine.update(1.0, {"A.y": 0.0}) == {"WTS.One": 10.0}

    def test_constant_expression_no_placeholders(self):
        op = build("2 * pi", inputs=("A.x",))
        assert op.apply_vector(0.0, [1.0], [0.0]) == pytest.approx(2 * math.pi)


class TestNoSampleInvariants:
    def test_division_by_zero_emits_nothing(self):
        series = collect(
            VirtualSignalEngine(
                [sig_def("R", ["A.x", "A.y"], [{"type": "expr", "expression": "%s / %s"}])]
            ),
            [(0.0, {"A.x": 400.0, "A.y": 0.0})],
        )
        assert "WTS.R" not in series

    def test_overflow_emits_nothing(self):
        op = build("1 / %s ** 2", inputs=("A.x",))
        assert op.apply_vector(0.0, [1e-200], [0.0]) is None

    def test_domain_error_emits_nothing(self):
        op = build("sqrt(%s)", inputs=("A.x",))
        assert op.apply_vector(0.0, [-1.0], [0.0]) is None

    def test_wrong_function_arity_emits_nothing(self):
        op = build("sqrt(%s, %s)")
        assert op.apply_vector(0.0, [4.0, 9.0], [0, 0]) is None


class TestValidation:
    def test_too_many_placeholders_for_inputs(self):
        definition = sig_def(
            "R", ["A.x"], [{"type": "expr", "expression": "%s / %s"}]
        )
        with pytest.raises(WtsValidationError) as excinfo:
            VirtualSignalEngine([definition])
        assert excinfo.value.errors[0]["code"] == "op_arity"

    @pytest.mark.parametrize(
        "expression",
        [
            "foo(%s)",
            "__import__('os').system('x')",
            "%s.real",
            "%s > 1",
            "%s if %s else 1",
            "lambda: %s",
            "%s +",
        ],
    )
    def test_rejected_expressions(self, expression):
        definition = sig_def("R", ["A.x", "A.y"], [{"type": "expr", "expression": expression}])
        with pytest.raises(WtsValidationError) as excinfo:
            VirtualSignalEngine([definition])
        assert excinfo.value.errors[0]["code"] == "op_params"

    def test_unknown_name_rejected(self):
        with pytest.raises(OpError):
            compile_expression("foo + 1")

    def test_string_literal_rejected(self):
        with pytest.raises(OpError):
            compile_expression("'%s'")

    def test_bool_literal_rejected(self):
        with pytest.raises(OpError):
            compile_expression("True")

    def test_keyword_argument_rejected(self):
        with pytest.raises(OpError):
            compile_expression("min(%s, x=1)")

    def test_compiled_tree_evaluates(self):
        tree, count = compile_expression("%s + %s")
        assert count == 2
        assert evaluate_expression(tree, [2.0, 5.0]) == 7.0

    def test_reserved_slot_name_rejected(self):
        # "v1" is not a placeholder and no "%s" defined it.
        with pytest.raises(OpError):
            compile_expression("%s + v1")

    def test_registered_in_catalog(self):
        assert OPS["expr"] is ExprOp
        assert ExprOp.is_head and ExprOp.arity == (1, None)


class TestParity:
    """I4: streaming and batch paths agree for expression definitions."""

    def _definitions(self):
        return [
            sig_def(
                "Ratio",
                ["A.x", "A.y"],
                [{"type": "expr", "expression": "%s / %s"},
                 {"type": "bias", "offset": 1.0}],
            ),
            sig_def(
                "Offset",
                ["A.x"],
                [{"type": "expr", "expression": "%s - 300"}],
            ),
        ]

    def test_streaming_equals_batch(self):
        groups = [
            (0.0, {"A.x": 400.0, "A.y": 200.0}),
            (1.0, {"A.x": 100.0, "A.y": 400.0}),
            (2.0, {"A.x": 500.0, "A.y": 250.0}),
        ]
        streaming = collect(VirtualSignalEngine(self._definitions()), groups)
        rows = sorted(
            (ts, signal_id, value)
            for ts, values in groups
            for signal_id, value in values.items()
        )
        batched: dict[str, list[tuple[float, float]]] = {}
        for ts, signal_id, value in run_batch(
            VirtualSignalEngine(self._definitions()), rows
        ):
            batched.setdefault(signal_id, []).append((ts, value))
        assert batched == streaming
        assert batched
