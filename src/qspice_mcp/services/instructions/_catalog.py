"""Compatibility re-exports for workflow instruction catalog access."""

from __future__ import annotations

from qspice_mcp.services.recipes._catalog import (
    WorkflowInstructionEntry,
    list_workflow_instruction_entries,
    read_workflow_instruction_markdown,
    resolve_workflow_instruction_entry,
)

__all__ = [
    "WorkflowInstructionEntry",
    "list_workflow_instruction_entries",
    "read_workflow_instruction_markdown",
    "resolve_workflow_instruction_entry",
]
