"""Head operation: user-defined arithmetic expressions over the inputs.

Each literal ``%s`` in the expression binds to one selected signal, in
selection order (``%s / %s`` for a front/rear brake ratio). The text is
compiled once into a restricted abstract-syntax tree: only numbers, the
placeholder names ``v0..vN``, a fixed function table, ``pi``/``e``, and
arithmetic operators survive. Nothing here interprets arbitrary user code:
the tree is walked node by node against a whitelist, so no dunder lookup,
attribute access, import, or call outside the table can occur.
"""
from __future__ import annotations

import ast
import math
import re
from typing import Any, Sequence

from wts.errors import OpError
from wts.ops import register
from wts.ops.base import HeadOp, ParamSpec

#: Functions callable from an expression, in order of the help text.
_FUNCS: dict[str, Any] = {
    "abs": abs,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "floor": math.floor,
    "ceil": math.ceil,
}

_CONSTS: dict[str, float] = {"pi": math.pi, "e": math.e}

_PLACEHOLDER = re.compile(r"%s")
_SLOT = re.compile(r"^v(\d+)$")

_ALLOWED_NODES = frozenset(
    {
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Name,
        ast.Call,
        ast.Load,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.Pow,
        ast.UAdd,
        ast.USub,
    }
)

_BIN_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
}

_UNARY_OPS = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}

_NODE_REASONS = {
    "Attribute": "attribute access",
    "Subscript": "indexing",
    "Tuple": "tuples",
    "List": "lists",
    "Dict": "dicts",
    "Set": "sets",
    "Compare": "comparison",
    "BoolOp": "boolean logic",
    "IfExp": "conditional expressions",
    "Lambda": "lambda",
    "JoinedStr": "string interpolation",
    "FormattedValue": "string interpolation",
    "Starred": "argument unpacking",
    "Slice": "slicing",
    "ListComp": "comprehensions",
    "SetComp": "comprehensions",
    "DictComp": "comprehensions",
    "GeneratorExp": "comprehensions",
    "NamedExpr": "assignment expressions",
    "Await": "await",
    "Yield": "yield",
    "YieldFrom": "yield",
}


def _reason(node_cls: type) -> str:
    return _NODE_REASONS.get(node_cls.__name__, node_cls.__name__.lower())


def compile_expression(text: str) -> tuple[ast.Expression, int]:
    """Turn expression text into a whitelisted tree plus placeholder count.

    Each literal ``%s`` is substituted left-to-right with ``v0``, ``v1``, …;
    a ``%`` not followed by ``s`` is left alone, so ``%s % 10`` stays modulo.
    ``^`` is rewritten to ``**`` so it means calculator-style power (Python
    would read it as bitwise xor, which stays outside the whitelist).
    Raises :class:`OpError` on a syntax error or any construct outside the
    arithmetic whitelist.
    """
    slot_count = 0

    def _replace(_match: re.Match) -> str:
        nonlocal slot_count
        replacement = f"v{slot_count}"
        slot_count += 1
        return replacement

    substituted = _PLACEHOLDER.sub(_replace, text).replace("^", "**")
    try:
        tree = ast.parse(substituted, mode="eval")
    except SyntaxError as exc:
        raise OpError(
            f"could not parse expression at column {exc.offset}: {exc.msg}"
        ) from None
    except (ValueError, RecursionError, MemoryError) as exc:
        raise OpError(f"could not parse expression: {exc}") from None
    _validate_tree(tree, slot_count)
    return tree, slot_count


def _validate_tree(tree: ast.Expression, slot_count: int) -> None:
    """Iterative whitelist walk; rejects anything non-arithmetic."""
    stack: list[ast.AST] = [tree]
    max_slot = -1
    while stack:
        node = stack.pop()
        node_cls = type(node)
        if node_cls not in _ALLOWED_NODES:
            raise OpError(f"expression is not allowed: {_reason(node_cls)}")
        if node_cls is ast.Constant:
            value = node.value  # type: ignore[attr-defined]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise OpError(
                    "expression is not allowed: only numbers are permitted "
                    "as literals"
                )
        elif node_cls is ast.Name:
            name = node.id  # type: ignore[attr-defined]
            if name in _CONSTS:
                pass
            elif _SLOT.fullmatch(name):
                max_slot = max(max_slot, int(name[1:]))
            else:
                raise OpError(
                    f"expression is not allowed: unknown name '{name}'"
                )
        elif node_cls is ast.Call:
            func = node.func  # type: ignore[attr-defined]
            if not isinstance(func, ast.Name) or func.id not in _FUNCS:
                shown = (
                    func.id if isinstance(func, ast.Name) else _reason(type(func))
                )
                raise OpError(
                    f"expression is not allowed: unknown function '{shown}'"
                )
            if node.keywords:  # type: ignore[attr-defined]
                raise OpError(
                    "expression is not allowed: keyword arguments"
                )
            # Walk the arguments but never the function name itself.
            stack.extend(node.args)  # type: ignore[attr-defined]
            continue
        stack.extend(ast.iter_child_nodes(node))
    if max_slot >= slot_count:
        raise OpError(
            f"expression references signal v{max_slot} but only "
            f"{slot_count} '%s' placeholder(s) are present"
        )


def evaluate_expression(
    tree: ast.Expression, values: Sequence[float]
) -> float:
    """Evaluate a previously compiled tree against one input vector."""
    return _evaluate_node(tree.body, values)


def _evaluate_node(node: ast.AST, values: Sequence[float]) -> Any:
    node_cls = type(node)
    if node_cls is ast.Constant:
        return node.value  # type: ignore[attr-defined,no-any-return]
    if node_cls is ast.Name:
        name = node.id  # type: ignore[attr-defined]
        if name in _CONSTS:
            return _CONSTS[name]
        return values[int(name[1:])]
    if node_cls is ast.Call:
        func = _FUNCS[node.func.id]  # type: ignore[attr-defined]
        return func(
            *[_evaluate_node(arg, values) for arg in node.args]  # type: ignore[attr-defined]
        )
    if node_cls is ast.BinOp:
        left = _evaluate_node(node.left, values)  # type: ignore[attr-defined]
        right = _evaluate_node(node.right, values)  # type: ignore[attr-defined]
        op_cls = type(node.op)  # type: ignore[attr-defined]
        if op_cls is ast.Pow:
            # Coerce to float: integer exponentiation of huge operands could
            # burn unbounded time and memory; float pow overflows instead.
            return float(left) ** float(right)
        handler = _BIN_OPS.get(op_cls)
        if handler is None:
            raise OpError(f"expression is not allowed: operator '{_reason(op_cls)}'")
        return handler(left, right)
    if node_cls is ast.UnaryOp:
        operand = _evaluate_node(node.operand, values)  # type: ignore[attr-defined]
        handler = _UNARY_OPS.get(type(node.op))  # type: ignore[attr-defined]
        if handler is None:
            raise OpError(
                f"expression is not allowed: operator "
                f"'{_reason(type(node.op))}'"  # type: ignore[attr-defined]
            )
        return handler(operand)
    raise OpError(f"expression is not allowed: {_reason(node_cls)}")


@register
class ExprOp(HeadOp):
    """Arbitrary arithmetic across the inputs, in input order.

    ``%s`` marks one input slot; ``%s / %s`` divides the first selected
    signal by the second. A placeholder count below the input count is
    allowed (unreferenced inputs still gate emission); a constant
    expression with zero placeholders is valid too. Any arithmetic fault
    (division by zero, ``sqrt`` of a negative, overflow) emits *no sample*.
    """

    type = "expr"
    label = "Expression"
    arity = (1, None)
    params = (
        ParamSpec(
            name="expression",
            type="string",
            required=True,
            default=None,
            help=(
                "Use %s for each selected signal, in order, e.g. %s / %s or "
                "%s - 300. Supports + - * / // % ^ ** ( ) (^ raises to a "
                "power), functions abs min max sqrt exp log log10 sin cos "
                "tan asin acos atan atan2 floor ceil, and constants pi, e. "
                "A sample is emitted only once every selected signal has "
                "arrived."
            ),
        ),
    )

    def __init__(self, **params: Any) -> None:
        super().__init__(**params)
        self._tree, self._placeholders = compile_expression(self.expression)

    def check_arity(self, input_count: int) -> None:
        super().check_arity(input_count)
        if self._placeholders > input_count:
            raise OpError(
                f"expression uses {self._placeholders} '%s' placeholders but "
                f"only {input_count} signal(s) are selected"
            )

    def apply_vector(
        self, ts: float, values: Sequence[float], stamps: Sequence[float]
    ) -> float | None:
        try:
            return float(evaluate_expression(self._tree, values))
        except (
            ZeroDivisionError,
            OverflowError,
            ValueError,
            TypeError,
            RecursionError,
            IndexError,
        ):
            return None
