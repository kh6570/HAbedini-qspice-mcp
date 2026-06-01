"""Live GUI tool metadata."""

from __future__ import annotations

from .common import _ann

LIVE_GUI_TOOL_METADATA: dict[str, dict[str, object]] = {
    "refresh_schematic_in_gui": {
        "title": "Refresh Schematic In GUI",
        "description": (
            "Refresh one workspace-local .qsch GUI view on Windows by reopening via OS "
            "association or by force-restarting QSpice before reopening."
        ),
        "input_schema": {
            "type": "object",
            "required": ["schematic_path"],
            "properties": {
                "schematic_path": {"type": "string"},
                "strategy": {
                    "type": "string",
                    "enum": ["reopen_via_association", "restart_qspice_and_reopen"],
                },
                "force_restart": {"type": "boolean"},
            },
        },
        "annotations": _ann(),
    },
    "open_schematic_in_gui": {
        "title": "Open Schematic In GUI",
        "description": (
            "Open one workspace-local .qsch file through the local Windows OS file "
            "association as a convenience launcher."
        ),
        "input_schema": {
            "type": "object",
            "required": ["schematic_path"],
            "properties": {
                "schematic_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "describe_live_gui_support": {
        "title": "Describe Live GUI Support",
        "description": (
            "Describe the optional Windows-only live GUI layer, including its version gate, "
            "bridge-launch state, and external-bridge requirement."
        ),
        "input_schema": {"type": "object", "properties": {}},
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "scaffold_live_gui_session": {
        "title": "Scaffold Live GUI Session",
        "description": (
            "Generate a version-gated JSON manifest for an external Windows-message bridge "
            "that owns optional live GUI orchestration and cross-probing."
        ),
        "input_schema": {
            "type": "object",
            "required": ["session_name"],
            "properties": {
                "session_name": {"type": "string"},
                "schematic_path": {"type": "string"},
                "waveform_names": {"type": "array", "items": {"type": "string"}},
                "cross_probe_signals": {"type": "array", "items": {"type": "string"}},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "launch_live_gui_session": {
        "title": "Launch Live GUI Session",
        "description": (
            "Launch a version-gated live GUI session through the configured external "
            "Windows-message bridge command."
        ),
        "input_schema": {
            "type": "object",
            "required": ["session_name"],
            "properties": {
                "session_name": {"type": "string"},
                "schematic_path": {"type": "string"},
                "waveform_names": {"type": "array", "items": {"type": "string"}},
                "cross_probe_signals": {"type": "array", "items": {"type": "string"}},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "poll_live_gui_session": {
        "title": "Poll Live GUI Session",
        "description": "Read live or terminal status for one launched live GUI bridge session.",
        "input_schema": {
            "type": "object",
            "required": ["session_id"],
            "properties": {"session_id": {"type": "string"}},
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "send_live_gui_session_command": {
        "title": "Send Live GUI Session Command",
        "description": (
            "Queue one command for the external live GUI bridge to translate into "
            "Windows-message interaction for a launched session."
        ),
        "input_schema": {
            "type": "object",
            "required": ["session_id", "command"],
            "properties": {
                "session_id": {"type": "string"},
                "command": {"type": "string"},
                "signal": {"type": "string"},
                "payload": {"type": "object"},
            },
        },
        "annotations": _ann(),
    },
    "poll_live_gui_session_events": {
        "title": "Poll Live GUI Session Events",
        "description": (
            "Read persisted events emitted by the external live GUI bridge for one "
            "launched session."
        ),
        "input_schema": {
            "type": "object",
            "required": ["session_id"],
            "properties": {
                "session_id": {"type": "string"},
                "after_sequence": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "close_live_gui_session": {
        "title": "Close Live GUI Session",
        "description": (
            "Close one launched live GUI bridge session and optionally delete its manifest."
        ),
        "input_schema": {
            "type": "object",
            "required": ["session_id"],
            "properties": {
                "session_id": {"type": "string"},
                "delete_manifest": {"type": "boolean"},
            },
        },
        "annotations": _ann(),
    },
}


__all__ = ["LIVE_GUI_TOOL_METADATA"]
