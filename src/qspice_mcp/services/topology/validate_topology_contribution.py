"""Service validating a candidate topology-block manifest against the pack schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qspice_mcp.services.service_spec import ServiceSpec

_REQUIRED_STRING_FIELDS = ("block_id", "title", "category", "summary", "control_notes", "document")
_REQUIRED_OBJECT_LIST_FIELDS: dict[str, tuple[str, ...]] = {
    "ports": ("name", "role", "description"),
    "parameters": ("name", "description"),
    "design_equations": ("name", "expression", "description"),
}


@dataclass(frozen=True, slots=True)
class TopologyContributionValidation:
    """Outcome of validating one candidate topology-block manifest."""

    is_valid: bool
    block_id: str | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


SERVICE_SPEC = ServiceSpec(
    name="validate_topology_contribution",
    title="Validate Topology Contribution",
    summary="Validate a candidate topology-block manifest against the knowledge-pack schema.",
    phase="implemented",
    read_only=True,
)


def _validate_string_fields(manifest: dict[str, Any], errors: list[str]) -> None:
    for field in _REQUIRED_STRING_FIELDS:
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Field {field!r} is required and must be a non-empty string.")


def _validate_tags(manifest: dict[str, Any], errors: list[str]) -> None:
    tags = manifest.get("tags")
    if not isinstance(tags, list) or not tags:
        errors.append("Field 'tags' is required and must be a non-empty array.")
        return
    if any(not isinstance(tag, str) or not tag.strip() for tag in tags):
        errors.append("Field 'tags' must contain only non-empty strings.")


def _validate_object_lists(manifest: dict[str, Any], errors: list[str]) -> None:
    for field, required_keys in _REQUIRED_OBJECT_LIST_FIELDS.items():
        entries = manifest.get(field)
        if not isinstance(entries, list) or not entries:
            errors.append(f"Field {field!r} is required and must be a non-empty array of objects.")
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                errors.append(f"{field}[{index}] must be an object.")
                continue
            for key in required_keys:
                value = entry.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{field}[{index}] is missing required non-empty key {key!r}.")


def _validate_reference(manifest: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    reference = manifest.get("reference")
    if not isinstance(reference, dict):
        errors.append("Field 'reference' is required and must be an object.")
        return
    source = reference.get("source")
    if not isinstance(source, str) or not source.strip():
        errors.append("Field 'reference.source' is required and must be a non-empty string.")
    if not reference.get("url") and not reference.get("isbn"):
        warnings.append("reference should include a 'url' or 'isbn' for traceability.")


def validate_topology_contribution(manifest: dict[str, Any]) -> TopologyContributionValidation:
    """Validate a candidate topology-block manifest and report errors and warnings."""

    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(manifest, dict):
        return TopologyContributionValidation(
            is_valid=False,
            block_id=None,
            errors=("manifest must be a JSON object.",),
            warnings=(),
        )

    _validate_string_fields(manifest, errors)
    _validate_tags(manifest, errors)
    _validate_object_lists(manifest, errors)
    _validate_reference(manifest, errors, warnings)

    raw_block_id = manifest.get("block_id")
    block_id = (
        raw_block_id.strip() if isinstance(raw_block_id, str) and raw_block_id.strip() else None
    )
    if block_id is not None and not block_id.replace("_", "").isalnum():
        errors.append("block_id must contain only alphanumeric characters and underscores.")

    return TopologyContributionValidation(
        is_valid=not errors,
        block_id=block_id,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


__all__ = [
    "SERVICE_SPEC",
    "TopologyContributionValidation",
    "validate_topology_contribution",
]
