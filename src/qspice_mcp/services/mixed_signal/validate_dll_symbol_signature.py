"""Validate one schematic `.DLL` symbol against a C or C++ source file."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import (
    open_schematic_editor,
    read_component_symbol_metadata,
)
from qspice_mcp.services._internals.dll_contracts import (
    build_dll_symbol_contract,
    find_matching_export_name,
    parse_dll_source_contract_text,
)
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class DllSymbolSignatureValidation:
    """Validation summary for one `.DLL` schematic block and source file pair."""

    schematic_path: Path
    source_path: Path
    reference: str
    device_name: str
    expected_export_name: str
    matched_export_name: str | None
    exported_function_names: tuple[str, ...]
    symbol_input_pin_names: tuple[str, ...]
    symbol_output_pin_names: tuple[str, ...]
    source_input_pin_names: tuple[str, ...]
    source_output_pin_names: tuple[str, ...]
    is_valid: bool
    mismatches: tuple[str, ...]
    warnings: tuple[str, ...]


SERVICE_SPEC = ServiceSpec(
    name="validate_dll_symbol_signature",
    title="Validate DLL Symbol Signature",
    summary=(
        "Cross-check one `.DLL` schematic symbol against a C or C++ source file, "
        "including "
        "export name, pin count, ordering, and input/output labels."
    ),
    phase="implemented",
    read_only=True,
)


def validate_dll_symbol_signature(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    source_path: str | Path,
) -> DllSymbolSignatureValidation:
    """Validate one `.DLL` schematic block against one source artifact."""

    editor, resolved_schematic_path, _ = open_schematic_editor(
        schematic_path,
        workspace_root=workspace_root.resolve(strict=False),
    )
    symbol_metadata = read_component_symbol_metadata(editor, reference=reference)
    symbol_contract = build_dll_symbol_contract(
        reference=reference,
        device_name=str(editor.get_component_value(reference)),
        metadata=symbol_metadata,
    )

    resolved_source_path = validate_existing_file(
        source_path,
        workspace_root=workspace_root,
        suffixes=(".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"),
    )
    source_contract = parse_dll_source_contract_text(
        resolved_source_path.read_text(encoding="utf-8"),
        source_path=resolved_source_path,
    )

    matched_export_name = find_matching_export_name(
        symbol_contract.expected_export_name,
        source_contract.exported_function_names,
    )

    mismatches: list[str] = []
    warnings = list(source_contract.warnings)

    if matched_export_name is None:
        exported_names = ", ".join(source_contract.exported_function_names) or "none"
        mismatches.append(
            "Expected exported entry point matching "
            f"{symbol_contract.expected_export_name!r}; found {exported_names}."
        )

    if not source_contract.pins:
        mismatches.append("Source pin mappings could not be derived from `data[]` assignments.")
    else:
        if len(source_contract.pins) != len(symbol_contract.pins):
            mismatches.append(
                "Pin count mismatch: "
                f"symbol has {len(symbol_contract.pins)}, source exposes "
                f"{len(source_contract.pins)}."
            )
        if source_contract.input_pin_names != symbol_contract.input_pin_names:
            mismatches.append(
                "Input pin mismatch: "
                f"symbol {symbol_contract.input_pin_names}, "
                f"source {source_contract.input_pin_names}."
            )
        if source_contract.output_pin_names != symbol_contract.output_pin_names:
            mismatches.append(
                "Output pin mismatch: "
                f"symbol {symbol_contract.output_pin_names}, "
                f"source {source_contract.output_pin_names}."
            )

    return DllSymbolSignatureValidation(
        schematic_path=resolved_schematic_path,
        source_path=resolved_source_path,
        reference=reference,
        device_name=symbol_contract.device_name,
        expected_export_name=symbol_contract.expected_export_name,
        matched_export_name=matched_export_name,
        exported_function_names=source_contract.exported_function_names,
        symbol_input_pin_names=symbol_contract.input_pin_names,
        symbol_output_pin_names=symbol_contract.output_pin_names,
        source_input_pin_names=source_contract.input_pin_names,
        source_output_pin_names=source_contract.output_pin_names,
        is_valid=not mismatches,
        mismatches=tuple(mismatches),
        warnings=tuple(warnings),
    )


__all__ = [
    "SERVICE_SPEC",
    "DllSymbolSignatureValidation",
    "validate_dll_symbol_signature",
]
