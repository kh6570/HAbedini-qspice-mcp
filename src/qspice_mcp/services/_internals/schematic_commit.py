# In the name of God, the Most Gracious, the Most Merciful
"""Hash-guarded schematic writes and the ERC delta from one save."""

from __future__ import annotations

from collections import Counter
from contextvars import ContextVar, Token
from dataclasses import dataclass
from pathlib import Path

from mcp_app_core.commit import commit_file, content_sha256
from mcp_app_core.errors import ArtifactMissingError as CoreArtifactMissingError
from mcp_app_core.errors import ContentConflictError as CoreContentConflictError
from mcp_app_core.errors import ValidationError as CoreValidationError

from qspice_mcp.core.exceptions import (
    ArtifactMissingError,
    ContentConflictError,
    QSpiceError,
    ValidationError,
)
from qspice_mcp.services.schematic._connectivity import build_connectivity
from qspice_mcp.services.schematic._erc import ErcFinding, evaluate_schematic_connectivity

_READS: dict[str, str] = {}
_expected_hash: ContextVar[str | None] = ContextVar("schematic_expected_hash", default=None)


@dataclass(frozen=True, slots=True)
class SchematicEditReport:
    """Old ERC findings and the findings one save introduced."""

    content_sha256: str
    prior_findings: tuple[dict[str, object], ...]
    introduced_findings: tuple[dict[str, object], ...]


_edit_report: ContextVar[SchematicEditReport | None] = ContextVar(
    "schematic_edit_report",
    default=None,
)


def _path_key(path: Path) -> str:
    return str(Path(path).resolve(strict=False)).casefold()


def remember_schematic_content(path: Path, content: bytes) -> str:
    """Record the hash of schematic bytes that were just read or written."""

    digest = content_sha256(content)
    _READS[_path_key(path)] = digest
    return digest


def remember_schematic_read(path: Path) -> str:
    """Record the hash of one schematic file and return it."""

    target = Path(path)
    return remember_schematic_content(target, target.read_bytes())


def bind_expected_schematic_hash(value: object) -> Token[str | None]:
    """Use one caller-supplied hash for the schematic save inside this call."""

    if not isinstance(value, str) or not value.strip():
        return _expected_hash.set(None)
    return _expected_hash.set(value.strip())


def reset_expected_schematic_hash(token: Token[str | None]) -> None:
    """Restore the expected-hash context from ``bind_expected_schematic_hash``."""

    _expected_hash.reset(token)


def clear_schematic_edit_report() -> None:
    """Drop a report left by an earlier save in this context."""

    _edit_report.set(None)


def take_schematic_edit_report() -> SchematicEditReport | None:
    """Return and clear the report published by the latest schematic save."""

    report = _edit_report.get()
    _edit_report.set(None)
    return report


def attach_schematic_edit_report(payload: dict[str, object]) -> dict[str, object]:
    """Add the latest save's hash and ERC split to one tool reply."""

    report = take_schematic_edit_report()
    if report is None:
        return payload
    payload["content_sha256"] = report.content_sha256
    payload["prior_findings"] = [dict(item) for item in report.prior_findings]
    payload["introduced_findings"] = [dict(item) for item in report.introduced_findings]
    return payload


def _finding_key(finding: ErcFinding) -> tuple[str, str, str, str | None]:
    return (finding.severity, finding.code, finding.message, finding.location)


def _finding_payload(finding: ErcFinding) -> dict[str, object]:
    return {
        "severity": finding.severity,
        "code": finding.code,
        "message": finding.message,
        "fixable": finding.fixable,
        "location": finding.location,
    }


def _schematic_findings(path: Path) -> tuple[ErcFinding, ...]:
    if not path.is_file():
        return ()
    try:
        report = evaluate_schematic_connectivity(build_connectivity(path))
    except (OSError, QSpiceError, ValueError):
        return ()
    return report.findings


def publish_schematic_edit_report(
    path: Path,
    *,
    prior: tuple[ErcFinding, ...],
    content_hash: str,
) -> SchematicEditReport:
    """Store old findings and the findings present only after this save."""

    current = _schematic_findings(path)
    remaining = Counter(_finding_key(finding) for finding in prior)
    introduced: list[ErcFinding] = []
    for finding in current:
        key = _finding_key(finding)
        if remaining[key]:
            remaining[key] -= 1
            continue
        introduced.append(finding)
    report = SchematicEditReport(
        content_sha256=content_hash,
        prior_findings=tuple(_finding_payload(finding) for finding in prior),
        introduced_findings=tuple(_finding_payload(finding) for finding in introduced),
    )
    _edit_report.set(report)
    return report


def _expected_hash_for(path: Path) -> str:
    override = _expected_hash.get()
    if override is not None:
        return override
    remembered = _READS.get(_path_key(path))
    if remembered is not None:
        return remembered
    return remember_schematic_read(path)


def _write_new_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def commit_schematic_bytes(path: Path, content: bytes) -> str:
    """Write schematic bytes, using ``commit_file`` when the file already exists.

    An existing file is replaced only when its bytes still match the hash from
    the last read, or the hash the caller passed for this save. A mismatch
    raises ``ContentConflictError`` and leaves the file unchanged.
    """

    if not isinstance(content, bytes):
        raise ValidationError("Schematic save writes bytes.")
    target = Path(path)
    if not target.exists():
        _write_new_file(target, content)
        return remember_schematic_content(target, content)
    if not target.is_file():
        raise ValidationError("Schematic save path must be a file.")
    expected = _expected_hash_for(target)
    try:
        digest = commit_file(target, expected_hash=expected, content=content)
    except CoreContentConflictError as exc:
        raise ContentConflictError(
            "Refusing to write the schematic because its content hash does not match the last read.",  # noqa: E501
            expected_hash=exc.expected_hash,
            actual_hash=exc.actual_hash,
        ) from exc
    except CoreValidationError as exc:
        raise ValidationError(str(exc)) from exc
    except CoreArtifactMissingError as exc:
        raise ArtifactMissingError(str(exc)) from exc
    _READS[_path_key(target)] = digest
    return digest


def schematic_findings_before_save(path: Path) -> tuple[ErcFinding, ...]:
    """Return ERC findings for a schematic file before it is replaced."""

    return _schematic_findings(Path(path))


__all__ = [
    "SchematicEditReport",
    "attach_schematic_edit_report",
    "bind_expected_schematic_hash",
    "clear_schematic_edit_report",
    "commit_schematic_bytes",
    "publish_schematic_edit_report",
    "remember_schematic_content",
    "remember_schematic_read",
    "reset_expected_schematic_hash",
    "schematic_findings_before_save",
    "take_schematic_edit_report",
]
