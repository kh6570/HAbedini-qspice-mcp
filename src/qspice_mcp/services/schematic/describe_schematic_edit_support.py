"""Service describing which schematic edit intents are supported and how to reach them."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from qspice_mcp.services.service_spec import ServiceSpec

EditIntentName = Literal[
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


@dataclass(frozen=True, slots=True)
class IntentEntry:
    """One edit intent capability entry."""

    intent: EditIntentName
    label: str
    tool: str | None
    supported: bool
    requires_backend: bool
    preconditions: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SchematicEditSupport:
    """Machine-readable edit capability map for AI client go/no-go decisions."""

    supported_intents: tuple[IntentEntry, ...]


_INTENT_CATALOG: tuple[IntentEntry, ...] = (
    IntentEntry(
        intent="rename_reference",
        label="Rename component reference",
        tool="rename_component_reference",
        supported=True,
        requires_backend=False,
        preconditions=(
            "new_reference must not already exist in the schematic",
            "reference is case-insensitive unique",
        ),
        limitations=(),
    ),
    IntentEntry(
        intent="change_value",
        label="Change component value",
        tool="set_component_value",
        supported=True,
        requires_backend=False,
        preconditions=("component must have a value attribute",),
        limitations=(),
    ),
    IntentEntry(
        intent="change_model",
        label="Change component model",
        tool="set_element_model",
        supported=True,
        requires_backend=False,
        preconditions=(),
        limitations=(),
    ),
    IntentEntry(
        intent="edit_parameters",
        label="Edit component parameters",
        tool="set_component_parameters",
        supported=True,
        requires_backend=False,
        preconditions=(),
        limitations=("parameters are component-local, not schematic-level",),
    ),
    IntentEntry(
        intent="rotate_component",
        label="Rotate placed component",
        tool="set_component_rotation",
        supported=True,
        requires_backend=False,
        preconditions=("rotation_degrees must be a multiple of 45",),
        limitations=("Rotation updates pin attachment geometry; re-check wires after rotating.",),
    ),
    IntentEntry(
        intent="edit_symbol_text",
        label="Edit embedded symbol text (layout/style)",
        tool="set_component_symbol_text",
        supported=True,
        requires_backend=True,
        preconditions=(
            "a compatible editor backend must be installed",
            "reference-designator text must use rename_component_reference instead",
        ),
        limitations=("reference-designator text content is rejected by this tool",),
    ),
    IntentEntry(
        intent="edit_symbol_pin",
        label="Edit embedded symbol pin",
        tool="set_component_symbol_pin",
        supported=True,
        requires_backend=True,
        preconditions=(
            "a compatible editor backend must be installed",
            "component must have embedded symbol pins",
        ),
        limitations=(),
    ),
    IntentEntry(
        intent="edit_symbol_drawing",
        label="Edit embedded symbol drawing item",
        tool="set_component_symbol_drawing",
        supported=True,
        requires_backend=True,
        preconditions=(
            "a compatible editor backend must be installed",
            "component must have embedded symbol drawing items",
        ),
        limitations=(
            "add_component_symbol_drawing and remove_component_symbol_drawing "
            "are also available for insert/delete operations",
        ),
    ),
    IntentEntry(
        intent="delete_component",
        label="Delete component by reference",
        tool="remove_component",
        supported=True,
        requires_backend=False,
        preconditions=("component reference must exist in the schematic",),
        limitations=(),
    ),
)


SERVICE_SPEC = ServiceSpec(
    name="describe_schematic_edit_support",
    title="Describe Schematic Edit Support",
    summary=(
        "Return a static machine-readable capability map for every known schematic "
        "edit intent so AI clients can make deterministic go/no-go decisions "
        "before attempting writes."
    ),
    phase="implemented",
    read_only=True,
)


def describe_schematic_edit_support() -> SchematicEditSupport:
    """Return the static schematic edit capability map."""
    return SchematicEditSupport(supported_intents=_INTENT_CATALOG)


__all__ = [
    "SERVICE_SPEC",
    "EditIntentName",
    "IntentEntry",
    "SchematicEditSupport",
    "describe_schematic_edit_support",
]
