"""Service listing bundled workflow build instructions."""

from __future__ import annotations

from dataclasses import dataclass

from qspice_mcp.services.instructions._catalog import (
    WorkflowInstructionEntry,
    list_workflow_instruction_entries,
)
from qspice_mcp.services.service_spec import ServiceSpec

SERVICE_SPEC = ServiceSpec(
    name="list_workflow_instructions",
    title="List Workflow Instructions",
    summary="List bundled workflow instructions for scratch circuit authoring.",
    phase="implemented",
    read_only=True,
)


@dataclass(frozen=True, slots=True)
class WorkflowInstructionList:
    """Catalog of bundled workflow instructions."""

    instructions: tuple[WorkflowInstructionEntry, ...]


def list_workflow_instructions() -> WorkflowInstructionList:
    """Return every bundled workflow instruction entry."""

    return WorkflowInstructionList(instructions=list_workflow_instruction_entries())


__all__ = ["SERVICE_SPEC", "WorkflowInstructionList", "list_workflow_instructions"]
