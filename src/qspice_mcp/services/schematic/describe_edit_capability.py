"""Service for describing the edit capability for one schematic component intent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.services._backends.schematic_editor import (
    ComponentSymbolMetadata,
    open_schematic_editor,
    read_component_symbol_metadata,
)
from qspice_mcp.services.schematic.read_component import ComponentRead, read_component
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

EditIntent = Literal[
    "rename_reference",
    "change_value",
    "change_model",
    "edit_parameters",
    "rotate_component",
    "edit_symbol_text",
    "edit_symbol_pin",
    "edit_symbol_drawing",
    "delete_component",
]

_SUPPORTED_INTENTS: tuple[EditIntent, ...] = (
    "rename_reference",
    "change_value",
    "change_model",
    "edit_parameters",
    "rotate_component",
    "edit_symbol_text",
    "edit_symbol_pin",
    "edit_symbol_drawing",
    "delete_component",
)

_INTENT_TOOL_MAP: dict[EditIntent, str] = {
    "rename_reference": "rename_component_reference",
    "change_value": "set_component_value",
    "change_model": "set_element_model",
    "edit_parameters": "set_component_parameters",
    "rotate_component": "set_component_rotation",
    "edit_symbol_text": "set_component_symbol_text",
    "edit_symbol_pin": "set_component_symbol_pin",
    "edit_symbol_drawing": "set_component_symbol_drawing",
    "delete_component": "remove_component",
}


@dataclass(frozen=True, slots=True)
class EditCapability:
    """Preflight decision for one edit intent on one component."""

    schematic_path: Path
    reference: str
    component_kind: str
    intent: str
    supported: bool
    suggested_tool: str | None = None
    suggested_parameters: dict[str, object] = field(default_factory=dict)
    unsupported_reason: str | None = None
    nearest_alternatives: tuple[str, ...] = ()
    component_details: dict[str, object] = field(default_factory=dict)


SERVICE_SPEC = ServiceSpec(
    name="describe_edit_capability",
    title="Describe Edit Capability",
    summary=(
        "Perform a preflight check for one edit intent on a component: read its current "
        "state, map the intent to the correct tool, and return either a ready-to-execute "
        "suggestion or a clear explanation plus nearest valid alternatives."
    ),
    phase="implemented",
    read_only=True,
)


def describe_edit_capability(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    intent: EditIntent,
) -> EditCapability:
    """Return a preflight edit capability decision for one component intent."""

    normalized_intent = _normalize_intent(intent)
    resolved_workspace = workspace_root.resolve(strict=False)

    component = read_component(
        schematic_path,
        workspace_root=resolved_workspace,
        reference=reference,
    )

    symbol_metadata = _try_read_symbol_metadata(schematic_path, resolved_workspace, reference)
    details = _build_component_details(component, symbol_metadata)

    return _dispatch_intent(
        normalized_intent,
        component=component,
        symbol_metadata=symbol_metadata,
        details=details,
    )


def _try_read_symbol_metadata(
    schematic_path: str | Path,
    workspace_root: Path,
    reference: str,
) -> ComponentSymbolMetadata | None:
    try:
        editor, _, _ = open_schematic_editor(schematic_path, workspace_root=workspace_root)
        return read_component_symbol_metadata(editor, reference=reference)
    except (BackendUnavailableError, Exception):
        return None


def _build_component_details(
    component: ComponentRead,
    symbol_metadata: ComponentSymbolMetadata | None,
) -> dict[str, object]:
    details: dict[str, object] = {
        "kind": component.kind,
        "value": component.value,
        "description": component.description,
        "nodes": component.nodes,
        "parameters": component.parameters,
        "has_subcircuit": component.has_subcircuit,
        "position_x": component.position_x,
        "position_y": component.position_y,
        "rotation_degrees": component.rotation_degrees,
    }
    if symbol_metadata is not None:
        details["symbol_name"] = symbol_metadata.symbol_name
        details["text_count"] = len(symbol_metadata.text_attributes)
        details["pin_count"] = len(symbol_metadata.pins)
        details["drawing_count"] = len(symbol_metadata.drawing_items)
    return details


def _dispatch_intent(
    intent: EditIntent,
    *,
    component: ComponentRead,
    symbol_metadata: ComponentSymbolMetadata | None,
    details: dict[str, object],
) -> EditCapability:
    suggested_params: dict[str, object] = {
        "schematic_path": str(component.schematic_path),
        "reference": component.reference,
    }

    simple_intents: dict[EditIntent, tuple[str, dict[str, object] | None]] = {
        "delete_component": ("delete", None),
        "rename_reference": ("rename_reference", {"new_reference": ""}),
        "change_model": ("change_model", {"model": ""}),
        "edit_parameters": ("edit_parameters", {"parameters": component.parameters}),
        "rotate_component": (
            "rotate_component",
            {"rotation_degrees": component.rotation_degrees},
        ),
    }
    if intent in simple_intents:
        action_type, extra_params = simple_intents[intent]
        if action_type == "delete":
            return _make_edit_capability(
                component=component,
                intent=intent,
                details=details,
                supported=True,
                suggested_tool=_INTENT_TOOL_MAP[intent],
                suggested_parameters=suggested_params,
            )
        if extra_params is not None:
            suggested_params.update(extra_params)
        return _make_edit_capability(
            component=component,
            intent=intent,
            details=details,
            supported=True,
            suggested_tool=_INTENT_TOOL_MAP[intent],
            suggested_parameters=suggested_params,
        )

    if intent == "change_value":
        suggested_params["value"] = component.value or ""
        return _make_edit_capability(
            component=component,
            intent=intent,
            details=details,
            supported=component.value is not None,
            suggested_tool=_INTENT_TOOL_MAP[intent],
            suggested_parameters=suggested_params,
            unsupported_reason=(
                None
                if component.value is not None
                else "Component has no value attribute to change."
            ),
        )

    if symbol_metadata is None:
        return _make_edit_capability(
            component=component,
            intent=intent,
            details=details,
            supported=False,
            unsupported_reason=(
                f"Intent '{intent}' requires an editor backend "
                "to access embedded symbol metadata. "
                "No compatible editor backend is currently installed."
            ),
            nearest_alternatives=(
                "Install an editor backend via pip install qspice-mcp[backends]",
            ),
        )

    return _dispatch_symbol_intent(
        intent,
        component=component,
        details=details,
        symbol_metadata=symbol_metadata,
        suggested_params=suggested_params,
    )


def _make_edit_capability(
    *,
    component: ComponentRead,
    intent: EditIntent,
    details: dict[str, object],
    supported: bool = False,
    suggested_tool: str | None = None,
    suggested_parameters: dict[str, object] | None = None,
    unsupported_reason: str | None = None,
    nearest_alternatives: tuple[str, ...] = (),
) -> EditCapability:
    return EditCapability(
        schematic_path=component.schematic_path,
        reference=component.reference,
        component_kind=component.kind,
        intent=intent,
        component_details=details,
        supported=supported,
        suggested_tool=suggested_tool,
        suggested_parameters=suggested_parameters or {},
        unsupported_reason=unsupported_reason,
        nearest_alternatives=nearest_alternatives,
    )


def _dispatch_symbol_intent(
    intent: EditIntent,
    *,
    component: ComponentRead,
    details: dict[str, object],
    symbol_metadata: ComponentSymbolMetadata,
    suggested_params: dict[str, object],
) -> EditCapability:
    if intent == "edit_symbol_text":
        text_count = len(symbol_metadata.text_attributes)
        if text_count == 0:
            return _make_edit_capability(
                component=component,
                intent=intent,
                details=details,
                supported=False,
                unsupported_reason="Component has no embedded symbol text items to edit.",
            )
        suggested_params["text_index"] = None
        suggested_params["text_role"] = None
        return _make_edit_capability(
            component=component,
            intent=intent,
            details=details,
            supported=True,
            suggested_tool=_INTENT_TOOL_MAP[intent],
            suggested_parameters=suggested_params,
        )
    if intent == "edit_symbol_pin":
        pin_count = len(symbol_metadata.pins)
        if pin_count == 0:
            return _make_edit_capability(
                component=component,
                intent=intent,
                details=details,
                supported=False,
                unsupported_reason="Component has no embedded symbol pins to edit.",
            )
        pin_names = [p.name for p in symbol_metadata.pins]
        suggested_params["available_pin_names"] = pin_names
        return _make_edit_capability(
            component=component,
            intent=intent,
            details=details,
            supported=True,
            suggested_tool=_INTENT_TOOL_MAP[intent],
            suggested_parameters=suggested_params,
        )
    if intent == "edit_symbol_drawing":
        drawing_count = len(symbol_metadata.drawing_items)
        drawing_tags = list(symbol_metadata.drawing_tags)
        suggested_params["drawing_count"] = drawing_count
        suggested_params["available_drawing_tags"] = drawing_tags
        return _make_edit_capability(
            component=component,
            intent=intent,
            details=details,
            supported=True,
            suggested_tool=_INTENT_TOOL_MAP[intent],
            suggested_parameters=suggested_params,
        )
    return _make_edit_capability(
        component=component,
        intent=intent,
        details=details,
        supported=False,
        unsupported_reason=f"Unrecognized edit intent: {intent}",
        nearest_alternatives=tuple(_INTENT_TOOL_MAP.keys()),
    )


def _normalize_intent(raw: str) -> EditIntent:
    """Normalize and validate one edit intent token."""
    normalized = raw.strip().lower()
    for valid in _SUPPORTED_INTENTS:
        if normalized == valid:
            return valid
    raise ValueError(
        f"Unsupported edit intent: {raw!r}. Supported intents: {', '.join(_SUPPORTED_INTENTS)}"
    )


__all__ = [
    "SERVICE_SPEC",
    "EditCapability",
    "EditIntent",
    "describe_edit_capability",
]
