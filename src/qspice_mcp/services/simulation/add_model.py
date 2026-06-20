"""Append one SPICE model definition to a library or netlist artifact."""

from __future__ import annotations

from dataclasses import dataclass
from shutil import copy2
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._analysis_directive import (
    append_lines_before_end,
    resolve_staged_output_path,
)

if TYPE_CHECKING:
    from pathlib import Path

_TARGET_SUFFIXES = (".lib", ".inc", ".net", ".cir")
_MODEL_MIN_TOKENS = 2


@dataclass(frozen=True, slots=True)
class ModelDefinitionAdd:
    """Metadata for one appended model definition."""

    source_path: Path
    output_path: Path
    model_name: str | None
    line_count: int


SERVICE_SPEC = ServiceSpec(
    name="add_model",
    title="Add Model Definition",
    summary="Append one SPICE model definition block to a `.lib`, `.inc`, or netlist file.",
    phase="implemented",
    read_only=False,
)


def _normalize_model_lines(model_text: str) -> tuple[str, ...]:
    stripped = model_text.strip()
    if not stripped:
        raise ValidationError("model_text must not be empty.")
    lines = tuple(line.rstrip() for line in stripped.splitlines())
    if any(line.strip().lower() == ".end" for line in lines):
        raise ValidationError("model_text must not contain a standalone `.end` directive.")
    return lines


def _guess_model_name(lines: tuple[str, ...]) -> str | None:
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        tokens = stripped.split()
        if not tokens:
            continue
        if tokens[0].lower() == ".model" and len(tokens) >= _MODEL_MIN_TOKENS:
            return tokens[1]
        if tokens[0].startswith("."):
            continue
        return tokens[0]
    return None


def add_model(
    target_path: str | Path,
    *,
    workspace_root: Path,
    model_text: str,
    output_path: str | Path | None = None,
) -> ModelDefinitionAdd:
    """Append one model definition block to a workspace-local library or netlist file."""

    normalized_workspace = workspace_root.resolve(strict=False)
    source_path = validate_existing_file(
        target_path,
        workspace_root=normalized_workspace,
        suffixes=_TARGET_SUFFIXES,
    )
    destination = resolve_staged_output_path(
        output_path,
        workspace_root=normalized_workspace,
        default=source_path,
        allowed_suffixes=_TARGET_SUFFIXES,
    )
    if destination != source_path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        copy2(source_path, destination)

    model_lines = _normalize_model_lines(model_text)
    append_lines_before_end(destination, model_lines)
    return ModelDefinitionAdd(
        source_path=source_path,
        output_path=destination,
        model_name=_guess_model_name(model_lines),
        line_count=len(model_lines),
    )


__all__ = ["SERVICE_SPEC", "ModelDefinitionAdd", "add_model"]
