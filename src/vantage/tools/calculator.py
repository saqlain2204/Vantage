from __future__ import annotations

import ast
import operator
from typing import Any, Dict

from ..core.bases import ToolBase

# Guard against exponentiation towers like 9**9**9 that would compute for a very long time.
_MAX_POW_BASE = 1_000
_MAX_POW_EXP = 100


class Calculator(ToolBase):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluate a basic arithmetic expression."

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression, e.g. (2 + 3) * 4",
                },
            },
            "required": ["expression"],
            "additionalProperties": False,
        }

    def execute(self, **kwargs: Any) -> str:
        expr = str(kwargs.get("expression", ""))
        if not expr.strip():
            raise ValueError("expression is required")
        node = ast.parse(expr, mode="eval")
        value = _eval(node.body)
        return str(value)


_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval(node.left)
        right = _eval(node.right)
        if isinstance(node.op, ast.Pow):
            if abs(left) > _MAX_POW_BASE or abs(right) > _MAX_POW_EXP:
                raise ValueError(
                    f"Exponentiation operands are too large (base > {_MAX_POW_BASE} "
                    f"or exponent > {_MAX_POW_EXP})."
                )
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand))
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


