"""Service for evaluating arithmetic expressions over waveform traces."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from qspice_mcp.core.budgets import DEFAULT_BUDGET
from qspice_mcp.core.exceptions import BudgetExceededError, QSpiceError
from qspice_mcp.services._backends.waveform import (
    WaveformComponent,
    apply_budget,
    build_budget,
    load_waveform,
)
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from numpy.typing import NDArray

# A signal token looks like V(out), I(L1), Ix(...) — an identifier followed by
# a single parenthesised group that does not itself contain parentheses.
_SIGNAL_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\([^()]*\)")
_UNSUPPORTED_ELEMENT = (
    "Unsupported element in waveform expression; only signal tokens, numeric "
    "constants, parentheses, and + - * / ** operators are allowed."
)


@dataclass(frozen=True, slots=True)
class WaveformExpressionResult:
    """One evaluated waveform expression, ready for JSON serialization."""

    raw_path: Path
    expression: str
    plot_name: str | None
    axis_name: str | None
    signals: tuple[str, ...]
    step: int
    x_unit: str
    point_count: int
    original_point_count: int
    downsampled: bool
    x_values: tuple[float, ...]
    y_values: tuple[float, ...]


SERVICE_SPEC = ServiceSpec(
    name="evaluate_waveform_expression",
    title="Evaluate Waveform Expression",
    summary="Evaluate an arithmetic expression over one or more `.qraw` signals.",
    phase="implemented",
    read_only=True,
)


def _validate_response_budget(*, max_points: int | None, max_bytes: int | None) -> None:
    if max_points is not None and max_points > DEFAULT_BUDGET.max_points:
        raise BudgetExceededError(
            "evaluate_waveform_expression responses are capped at "
            f"{DEFAULT_BUDGET.max_points} points; narrow the window or use export tools."
        )
    if max_bytes is not None and max_bytes > DEFAULT_BUDGET.max_bytes:
        raise BudgetExceededError(
            "evaluate_waveform_expression responses are capped at "
            f"{DEFAULT_BUDGET.max_bytes} bytes; narrow the window or use export tools."
        )


def _substitute_signal_tokens(expression: str) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}

    def _replace(match: re.Match[str]) -> str:
        token = match.group(0)
        if token not in mapping:
            mapping[token] = f"_sig{len(mapping)}"
        return mapping[token]

    transformed = _SIGNAL_TOKEN.sub(_replace, expression)
    return transformed, mapping


def _evaluate_ast(node: ast.AST, variables: dict[str, NDArray[np.float64]]) -> Any:  # noqa: PLR0911
    if isinstance(node, ast.Expression):
        return _evaluate_ast(node.body, variables)
    if isinstance(node, ast.BinOp):
        left = _evaluate_ast(node.left, variables)
        right = _evaluate_ast(node.right, variables)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left**right
        raise QSpiceError(_UNSUPPORTED_ELEMENT)
    if isinstance(node, ast.UnaryOp):
        operand = _evaluate_ast(node.operand, variables)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        raise QSpiceError(_UNSUPPORTED_ELEMENT)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in variables:
        return variables[node.id]
    raise QSpiceError(_UNSUPPORTED_ELEMENT)


def evaluate_waveform_expression(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    expression: str,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    component: WaveformComponent = "auto",
    t_start: float | None = None,
    t_end: float | None = None,
    max_points: int | None = None,
    max_bytes: int | None = None,
) -> WaveformExpressionResult:
    """Evaluate one arithmetic expression over `.qraw` signals and return a bounded series."""

    _validate_response_budget(max_points=max_points, max_bytes=max_bytes)
    normalized_expression = expression.strip()
    if not normalized_expression:
        raise QSpiceError("expression must not be empty.")

    transformed, mapping = _substitute_signal_tokens(normalized_expression)
    if not mapping:
        raise QSpiceError(
            "expression must reference at least one signal, for example V(out)-V(in)."
        )

    resolved_workspace = workspace_root.resolve(strict=False)
    resolved_raw_path = validate_existing_file(
        raw_path, workspace_root=resolved_workspace, suffixes=(".qraw",)
    )

    variables: dict[str, NDArray[np.float64]] = {}
    axis: NDArray[np.float64] | None = None
    axis_name: str | None = None
    plot_name: str | None = None
    x_unit = ""
    resolved_step = 0
    resolved_signals: list[str] = []

    for token, placeholder in mapping.items():
        waveform = load_waveform(
            resolved_raw_path,
            workspace_root=resolved_workspace,
            signal=token,
            step=step,
            step_filters=step_filters,
            component=component,
            t_start=t_start,
            t_end=t_end,
        )
        if axis is None:
            axis = waveform.x
            axis_name = waveform.axis_name
            plot_name = waveform.plot_name
            x_unit = waveform.x_unit
            resolved_step = waveform.step
        elif waveform.x.shape != axis.shape:
            raise QSpiceError(
                f"Signal {waveform.signal} has {waveform.x.shape[0]} points but the "
                f"expression axis has {axis.shape[0]}; all signals must share one axis."
            )
        variables[placeholder] = waveform.y
        resolved_signals.append(waveform.signal)

    try:
        parsed = ast.parse(transformed, mode="eval")
    except SyntaxError as exc:
        raise QSpiceError(f"Could not parse waveform expression: {exc.msg}.") from exc

    evaluated = _evaluate_ast(parsed, variables)
    if axis is None:
        raise QSpiceError("expression did not resolve any signal axis.")
    result_values = np.asarray(evaluated, dtype=np.float64)
    if result_values.shape != axis.shape:
        result_values = np.broadcast_to(result_values, axis.shape).astype(np.float64)

    original_point_count = int(axis.shape[0])
    bounded_x, bounded_y, downsampled = apply_budget(
        axis,
        result_values,
        budget=build_budget(max_points=max_points, max_bytes=max_bytes),
    )
    return WaveformExpressionResult(
        raw_path=resolved_raw_path,
        expression=normalized_expression,
        plot_name=plot_name,
        axis_name=axis_name,
        signals=tuple(resolved_signals),
        step=resolved_step,
        x_unit=x_unit,
        point_count=int(bounded_x.shape[0]),
        original_point_count=original_point_count,
        downsampled=downsampled,
        x_values=tuple(float(value) for value in bounded_x.tolist()),
        y_values=tuple(float(value) for value in bounded_y.tolist()),
    )


__all__ = ["SERVICE_SPEC", "WaveformExpressionResult", "evaluate_waveform_expression"]
