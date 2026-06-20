"""Shared service metadata types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ServicePhase = Literal["planned", "implemented"]


@dataclass(frozen=True, slots=True)
class ServiceSpec:
    """Metadata for a planned application service."""

    name: str
    title: str
    summary: str
    phase: ServicePhase = "planned"
    read_only: bool = True
    long_running: bool = False
    destructive: bool = False
    idempotent: bool | None = None
    description: str | None = None
    input_schema: dict[str, object] | None = None
