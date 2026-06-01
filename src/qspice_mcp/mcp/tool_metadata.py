"""Grouped MCP tool metadata by capability area."""

from __future__ import annotations

from ._tool_metadata.artifact import ARTIFACT_TOOL_METADATA
from ._tool_metadata.batch import BATCH_TOOL_METADATA
from ._tool_metadata.live_gui import LIVE_GUI_TOOL_METADATA
from ._tool_metadata.mixed_signal import MIXED_SIGNAL_TOOL_METADATA
from ._tool_metadata.protocol import PROTOCOL_TOOL_METADATA
from ._tool_metadata.remote import REMOTE_TOOL_METADATA
from ._tool_metadata.recipes import RECIPES_TOOL_METADATA
from ._tool_metadata.schematic import SCHEMATIC_TOOL_METADATA
from ._tool_metadata.server import SERVER_TOOL_METADATA
from ._tool_metadata.simulation import SIMULATION_TOOL_METADATA
from ._tool_metadata.subcircuit import SUBCIRCUIT_TOOL_METADATA
from ._tool_metadata.waveform import WAVEFORM_TOOL_METADATA
from ._tool_metadata.workspace import WORKSPACE_TOOL_METADATA

TOOL_METADATA: dict[str, dict[str, object]] = {
    **SERVER_TOOL_METADATA,
    **BATCH_TOOL_METADATA,
    **REMOTE_TOOL_METADATA,
    **ARTIFACT_TOOL_METADATA,
    **SCHEMATIC_TOOL_METADATA,
    **SUBCIRCUIT_TOOL_METADATA,
    **SIMULATION_TOOL_METADATA,
    **WAVEFORM_TOOL_METADATA,
    **LIVE_GUI_TOOL_METADATA,
    **MIXED_SIGNAL_TOOL_METADATA,
    **PROTOCOL_TOOL_METADATA,
    **RECIPES_TOOL_METADATA,
    **WORKSPACE_TOOL_METADATA,
}

__all__ = [
    "ARTIFACT_TOOL_METADATA",
    "BATCH_TOOL_METADATA",
    "LIVE_GUI_TOOL_METADATA",
    "MIXED_SIGNAL_TOOL_METADATA",
    "PROTOCOL_TOOL_METADATA",
    "RECIPES_TOOL_METADATA",
    "REMOTE_TOOL_METADATA",
    "SCHEMATIC_TOOL_METADATA",
    "SERVER_TOOL_METADATA",
    "SIMULATION_TOOL_METADATA",
    "SUBCIRCUIT_TOOL_METADATA",
    "TOOL_METADATA",
    "WAVEFORM_TOOL_METADATA",
    "WORKSPACE_TOOL_METADATA",
]
