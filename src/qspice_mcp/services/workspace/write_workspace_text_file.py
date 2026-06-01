"""Write a sandboxed UTF-8 text file inside the workspace root."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services._shared.paths import resolve_workspace_output_path
from qspice_mcp.services.service_spec import ServiceSpec

_ALLOWED_SUFFIXES = (".cpp", ".h", ".hpp", ".c", ".txt", ".cmake", ".md")


@dataclass(frozen=True, slots=True)
class WrittenWorkspaceTextFile:
    """Metadata for one workspace text file write."""

    output_path: Path
    overwritten: bool
    byte_count: int
    line_count: int


SERVICE_SPEC = ServiceSpec(
    name="write_workspace_text_file",
    title="Write Workspace Text File",
    summary=(
        "Write or overwrite one UTF-8 text file inside the workspace root "
        "(for example a C-block `.cpp` source)."
    ),
    phase="implemented",
    read_only=False,
)


def write_workspace_text_file(
    relative_path: str | Path,
    *,
    workspace_root: Path,
    content: str,
    overwrite: bool = False,
) -> WrittenWorkspaceTextFile:
    """Write one UTF-8 text artifact under the configured workspace root."""

    destination = resolve_workspace_output_path(
        relative_path,
        workspace_root=workspace_root,
        default=workspace_root / Path(relative_path).name,
        suffixes=_ALLOWED_SUFFIXES,
    )
    if destination.exists() and not overwrite:
        raise ValidationError(f"File already exists (set overwrite=true): {destination}")

    overwritten = destination.exists()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8", newline="\n")
    normalized = content.replace("\r\n", "\n")
    return WrittenWorkspaceTextFile(
        output_path=destination,
        overwritten=overwritten,
        byte_count=len(normalized.encode("utf-8")),
        line_count=0 if normalized == "" else normalized.count("\n") + 1,
    )


__all__ = ["SERVICE_SPEC", "WrittenWorkspaceTextFile", "write_workspace_text_file"]
