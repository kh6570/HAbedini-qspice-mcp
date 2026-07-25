"""Service for reading one bundled workflow build instruction."""

from __future__ import annotations

from dataclasses import dataclass

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.instructions._catalog import (
    read_workflow_instruction_markdown,
    resolve_workflow_instruction_entry,
)
from qspice_mcp.services.service_spec import ServiceSpec

SERVICE_SPEC = ServiceSpec(
    name="read_workflow_instruction",
    title="Read Workflow Instruction",
    summary="Read one bundled workflow instruction document (for example buck-converter-cpp).",
    phase="implemented",
    read_only=True,
)


@dataclass(frozen=True, slots=True)
class WorkflowInstructionDocument:
    """One workflow instruction document."""

    instruction_id: str
    title: str
    summary: str
    track: str
    recipe_id: str
    related_instruction_id: str | None
    content: str
    content_length: int = 0
    content_truncated: bool = False


def read_workflow_instruction(
    instruction_id: str,
    *,
    max_chars: int | None = None,
) -> WorkflowInstructionDocument:
    """Return one workflow instruction document.

    ``max_chars`` returns only a leading excerpt of the markdown body;
    ``content_length`` always reports the full document size and
    ``content_truncated`` flags cuts.
    """

    if max_chars is not None and max_chars < 1:
        raise ValidationError("max_chars must be a positive integer.")
    entry = resolve_workflow_instruction_entry(instruction_id)
    content = read_workflow_instruction_markdown(entry.instruction_id)
    content_length = len(content)
    content_truncated = False
    if max_chars is not None and content_length > max_chars:
        content = content[:max_chars]
        content_truncated = True
    return WorkflowInstructionDocument(
        instruction_id=entry.instruction_id,
        title=entry.title,
        summary=entry.summary,
        track=entry.track,
        recipe_id=entry.recipe_id,
        related_instruction_id=entry.related_instruction_id,
        content=content,
        content_length=content_length,
        content_truncated=content_truncated,
    )


__all__ = ["SERVICE_SPEC", "WorkflowInstructionDocument", "read_workflow_instruction"]
