"""Shared schema-version helpers for persisted JSON artifacts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from qspice_mcp.core.exceptions import UnsupportedManifestVersionError, ValidationError

if TYPE_CHECKING:
    from collections.abc import Mapping

PERSISTED_SCHEMA_VERSION = 1
_LEGACY_SCHEMA_VERSION = 0


def stamp_schema_version(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a persisted payload with the current schema version stamped."""

    return {"schema_version": PERSISTED_SCHEMA_VERSION, **payload}


def validate_schema_version(
    payload: Mapping[str, object],
    *,
    artifact_name: str,
    allow_legacy_unversioned: bool = False,
) -> int:
    """Validate one persisted payload schema version.

    Versionless payloads can be treated as legacy schema `0` when the caller
    explicitly opts into a lightweight migration path.
    """

    raw_version = payload.get("schema_version")
    if raw_version is None:
        if allow_legacy_unversioned:
            return _LEGACY_SCHEMA_VERSION
        raise ValidationError(
            f"{artifact_name} is missing required schema_version {PERSISTED_SCHEMA_VERSION}."
        )
    if isinstance(raw_version, bool) or not isinstance(raw_version, int):
        raise ValidationError(
            f"{artifact_name} has invalid schema_version {raw_version!r}; expected integer "
            f"{PERSISTED_SCHEMA_VERSION}."
        )
    if raw_version == _LEGACY_SCHEMA_VERSION and allow_legacy_unversioned:
        return raw_version
    if raw_version != PERSISTED_SCHEMA_VERSION:
        raise UnsupportedManifestVersionError(
            f"{artifact_name} uses unsupported schema_version {raw_version}; supported "
            f"version is {PERSISTED_SCHEMA_VERSION}."
        )
    return raw_version


__all__ = ["PERSISTED_SCHEMA_VERSION", "stamp_schema_version", "validate_schema_version"]
