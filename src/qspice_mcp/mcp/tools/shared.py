"""Shared helpers for MCP tool handlers."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import TypeAlias, cast

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


def to_jsonable(value: object) -> JsonValue:
    """Convert service-layer return values into MCP-friendly JSON data."""

    if is_dataclass(value) and not isinstance(value, type):
        converted: JsonValue = {
            field.name: to_jsonable(getattr(value, field.name)) for field in fields(value)
        }
    elif isinstance(value, Path):
        converted = str(value)
    elif isinstance(value, Enum):
        converted = value.value
    elif isinstance(value, (datetime, date, time)):
        converted = value.isoformat()
    elif isinstance(value, dict):
        converted = {str(key): to_jsonable(item) for key, item in value.items()}
    elif isinstance(value, (list, tuple)):
        converted = [to_jsonable(item) for item in value]
    else:
        converted = cast("JsonValue", value)
    return converted


def to_json_object(value: object) -> dict[str, object]:
    """Convert one service result into a JSON-friendly mapping."""

    converted = to_jsonable(value)
    if not isinstance(converted, dict):
        raise TypeError("Expected a mapping-like service result.")
    return cast("dict[str, object]", converted)


__all__ = ["JsonScalar", "JsonValue", "to_json_object", "to_jsonable"]
