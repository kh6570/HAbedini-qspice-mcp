"""Schematic edit helpers: wiring."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.core.exceptions import ArtifactMissingError, QSpiceError, ValidationError

from ..clean_room_schematic import write_blank_schematic
from ..schematic_editor_backend import (
    _GROUND_NET_NAME,
    _NET_LABEL_FLAGS,
    _NET_LABEL_KIND,
    _NET_LABEL_STYLE_DEFAULT,
    _NET_LABEL_STYLE_GROUND,
    _format_qsch_point,
    _load_qsch_support_modules,
    _normalize_net_name,
    _QschEditorProtocol,
    _quote_qsch_string,
    _unquote_qsch_string,
    load_qsch_editor_factory,
    resolve_schematic_output_path,
)
from ..schematic_editor_geometry import resolve_component_pin_position, resolve_wire_points
from .structure import _append_schematic_tag, bootstrap_blank_schematic

if TYPE_CHECKING:
    from pathlib import Path


def add_net_label(
    editor: _QschEditorProtocol,
    *,
    net_name: str,
    position: tuple[int, int],
) -> str:
    """Add one net label to the current editor and return its normalized name."""

    normalized_net_name = _normalize_net_name(net_name)
    _validate_label_wire_names(editor, position=position, net_name=normalized_net_name)
    qsch_module, _ = _load_qsch_support_modules()
    style = (
        _NET_LABEL_STYLE_GROUND
        if normalized_net_name.upper() in {_GROUND_NET_NAME, "0"}
        else _NET_LABEL_STYLE_DEFAULT
    )
    label_tag = qsch_module.QschTag(
        "net",
        _format_qsch_point(position),
        _NET_LABEL_KIND,
        style,
        _NET_LABEL_FLAGS,
        _quote_qsch_string(normalized_net_name),
    )
    _append_schematic_tag(editor, label_tag)
    return normalized_net_name


def _validate_label_wire_names(
    editor: _QschEditorProtocol, *, position: tuple[int, int], net_name: str
) -> None:
    """Reject a label that contradicts the explicit name of a wire it touches."""

    if editor.schematic is None:
        return
    schematic_tree = cast("Any", editor.schematic)
    for wire in schematic_tree.get_items("wire"):
        if len(wire.tokens) <= 3:  # noqa: PLR2004
            continue
        wire_name = _unquote_qsch_string(str(wire.tokens[3]))
        if not wire_name or _net_name_key(wire_name) == _net_name_key(net_name):
            continue
        start = _parse_qsch_point(str(wire.tokens[1]))
        end = _parse_qsch_point(str(wire.tokens[2]))
        dx, dy = end[0] - start[0], end[1] - start[1]
        px, py = position[0] - start[0], position[1] - start[1]
        on_segment = (
            dx * py == dy * px
            and min(start[0], end[0]) <= position[0] <= max(start[0], end[0])
            and min(start[1], end[1]) <= position[1] <= max(start[1], end[1])
        )
        if on_segment:
            raise ValidationError(
                f"Net label {net_name!r} conflicts with explicit wire name {wire_name!r} "
                f"at {position}. Use rename_net to update all labels and named wires together."
            )


def _net_name_key(net_name: str) -> str:
    """Compare SPICE names while treating GND and 0 as the same ground net."""

    return "0" if net_name.upper() in {"GND", "0"} else net_name.casefold()


def add_junction(
    editor: _QschEditorProtocol,
    *,
    position: tuple[int, int],
) -> tuple[int, int]:
    """Add one junction node to the current editor."""

    bootstrap_blank_schematic(editor)
    qsch_module, _ = _load_qsch_support_modules()
    junction_tag = qsch_module.QschTag("junction", _format_qsch_point(position))
    _append_schematic_tag(editor, junction_tag)
    return position


def add_wire(
    editor: _QschEditorProtocol,
    *,
    start: tuple[int, int] | None = None,
    end: tuple[int, int] | None = None,
    start_reference: str | None = None,
    start_pin: str | None = None,
    end_reference: str | None = None,
    end_pin: str | None = None,
    net_name: str,
) -> str:
    """Add one wire segment to the current editor and return its normalized net name."""

    start_position, end_position = resolve_wire_points(
        editor,
        start=start,
        end=end,
        start_reference=start_reference,
        start_pin=start_pin,
        end_reference=end_reference,
        end_pin=end_pin,
    )
    normalized_net_name = _normalize_net_name(net_name)
    qsch_module, _ = _load_qsch_support_modules()
    wire_tag = qsch_module.QschTag(
        "wire",
        _format_qsch_point(start_position),
        _format_qsch_point(end_position),
        _quote_qsch_string(normalized_net_name),
    )
    _append_schematic_tag(editor, wire_tag)
    return normalized_net_name


_QSCH_POINT_PATTERN = re.compile(r"^\((-?\d+),(-?\d+)\)$")


def _parse_qsch_point(token: str) -> tuple[int, int]:
    match = _QSCH_POINT_PATTERN.match(str(token).strip())
    if match is None:
        raise ValueError(f"Invalid QSch point token: {token!r}")
    return int(match.group(1)), int(match.group(2))


def _wire_endpoints_match(
    first: tuple[int, int],
    second: tuple[int, int],
    *,
    target_start: tuple[int, int],
    target_end: tuple[int, int],
) -> bool:
    forward = first == target_start and second == target_end
    reverse = first == target_end and second == target_start
    return forward or reverse


def remove_wire(
    editor: _QschEditorProtocol,
    *,
    start: tuple[int, int] | None = None,
    end: tuple[int, int] | None = None,
    start_reference: str | None = None,
    start_pin: str | None = None,
    end_reference: str | None = None,
    end_pin: str | None = None,
    net_name: str | None = None,
) -> str:
    """Remove one wire segment matching the resolved endpoints and optional net name."""

    start_position, end_position = resolve_wire_points(
        editor,
        start=start,
        end=end,
        start_reference=start_reference,
        start_pin=start_pin,
        end_reference=end_reference,
        end_pin=end_pin,
    )
    normalized_net_name = _normalize_net_name(net_name) if net_name is not None else None
    if editor.schematic is None:
        raise QSpiceError("Editor does not expose a root schematic tree.")
    schematic_obj: Any = editor.schematic
    items = cast("list[Any]", schematic_obj.items)
    for index, tag in enumerate(list(items)):
        if getattr(tag, "tag", None) != "wire":
            continue
        tokens = list(getattr(tag, "tokens", ()))
        if len(tokens) < 3:  # noqa: PLR2004
            continue
        wire_start = _parse_qsch_point(str(tokens[1]))
        wire_end = _parse_qsch_point(str(tokens[2]))
        wire_net = _unquote_qsch_string(str(tokens[3])) if len(tokens) >= 4 else None  # noqa: PLR2004
        if normalized_net_name is not None and wire_net != normalized_net_name:
            continue
        if not _wire_endpoints_match(
            wire_start,
            wire_end,
            target_start=start_position,
            target_end=end_position,
        ):
            continue
        items.pop(index)
        editor.updated = True
        return wire_net or normalized_net_name or ""
    raise QSpiceError("No matching wire segment was found for the requested endpoints.")


def remove_net_label(
    editor: _QschEditorProtocol,
    *,
    position: tuple[int, int],
    net_name: str | None = None,
) -> str:
    """Remove one net label at the given position and optional net name."""

    normalized_net_name = _normalize_net_name(net_name) if net_name is not None else None
    if editor.schematic is None:
        raise QSpiceError("Editor does not expose a root schematic tree.")
    schematic_obj: Any = editor.schematic
    items = cast("list[Any]", schematic_obj.items)
    for index, tag in enumerate(list(items)):
        if getattr(tag, "tag", None) != "net":
            continue
        tokens = list(getattr(tag, "tokens", ()))
        if len(tokens) < 6:  # noqa: PLR2004
            continue
        label_position = _parse_qsch_point(str(tokens[1]))
        if label_position != position:
            continue
        label_net = _unquote_qsch_string(str(tokens[5]))
        if normalized_net_name is not None and label_net != normalized_net_name:
            continue
        items.pop(index)
        editor.updated = True
        return label_net or normalized_net_name or ""
    raise QSpiceError("No matching net label was found for the requested position.")


def remove_junction(
    editor: _QschEditorProtocol,
    *,
    position: tuple[int, int],
) -> tuple[int, int]:
    """Remove one junction node at the given position."""

    if editor.schematic is None:
        raise QSpiceError("Editor does not expose a root schematic tree.")
    schematic_obj: Any = editor.schematic
    items = cast("list[Any]", schematic_obj.items)
    for index, tag in enumerate(list(items)):
        if getattr(tag, "tag", None) != "junction":
            continue
        tokens = list(getattr(tag, "tokens", ()))
        if len(tokens) < 2:  # noqa: PLR2004
            continue
        junction_position = _parse_qsch_point(str(tokens[1]))
        if junction_position != position:
            continue
        items.pop(index)
        editor.updated = True
        return junction_position
    raise QSpiceError("No matching junction was found for the requested position.")


@dataclass(frozen=True, slots=True)
class OrphanConnectionCleanup:
    """Counts of dangling connection items pruned after a component removal."""

    wires_removed: int
    junctions_removed: int
    net_labels_removed: int


def collect_component_pin_coordinates(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> set[tuple[int, int]]:
    """Resolve the world coordinates of every pin on one component (best-effort)."""

    normalized_reference = reference.strip()
    coordinates: set[tuple[int, int]] = set()
    try:
        component = editor.get_component(normalized_reference)
    except (ValueError, QSpiceError):
        return coordinates
    for port in component.ports:
        try:
            coordinates.add(
                resolve_component_pin_position(
                    editor, reference=normalized_reference, pin_name=str(port)
                )
            )
        except (ValueError, QSpiceError):
            continue
    return coordinates


def _orphaned_connection_kind(tag: Any, coordinates: set[tuple[int, int]]) -> str | None:
    """Return 'wire'/'junction'/'net' when ``tag`` is orphaned at a coordinate, else None."""

    tag_name = getattr(tag, "tag", None)
    tokens = getattr(tag, "tokens", None)
    if tokens is None:
        return None

    def _point_at(index: int) -> tuple[int, int] | None:
        if len(tokens) <= index:
            return None
        try:
            return _parse_qsch_point(str(tokens[index]))
        except ValueError:
            return None

    if tag_name == "wire":
        if _point_at(1) in coordinates or _point_at(2) in coordinates:
            return "wire"
        return None
    if tag_name in {"junction", "net"} and _point_at(1) in coordinates:
        return cast("str", tag_name)
    return None


def _remove_orphaned_connections(
    editor: _QschEditorProtocol,
    coordinates: set[tuple[int, int]],
) -> OrphanConnectionCleanup:
    """Drop wires, junctions, and net labels that sit on now-orphaned coordinates."""

    if not coordinates or editor.schematic is None:
        return OrphanConnectionCleanup(0, 0, 0)
    schematic_obj: Any = editor.schematic
    items = cast("list[Any]", schematic_obj.items)
    kept: list[Any] = []
    counts = {"wire": 0, "junction": 0, "net": 0}
    for tag in items:
        kind = _orphaned_connection_kind(tag, coordinates)
        if kind is None:
            kept.append(tag)
        else:
            counts[kind] += 1
    if any(counts.values()):
        items[:] = kept
        editor.updated = True
    return OrphanConnectionCleanup(
        wires_removed=counts["wire"],
        junctions_removed=counts["junction"],
        net_labels_removed=counts["net"],
    )


def remove_component_with_orphan_cleanup(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    remove_orphan_wires: bool = False,
) -> OrphanConnectionCleanup:
    """Remove one component and optionally prune connection items it leaves dangling.

    A coordinate is "orphaned" when it was one of the removed component's pin
    positions and no remaining component pin still occupies it. Wires touching an
    orphaned coordinate and junctions/net labels sitting on one are removed.
    """

    normalized_reference = reference.strip()
    if not normalized_reference:
        raise ValueError("reference must not be empty.")

    removed_pin_coordinates = (
        collect_component_pin_coordinates(editor, reference=normalized_reference)
        if remove_orphan_wires
        else set()
    )

    editor.remove_component(normalized_reference)
    editor.updated = True

    if not remove_orphan_wires:
        return OrphanConnectionCleanup(0, 0, 0)

    remaining_pin_coordinates: set[tuple[int, int]] = set()
    for other_reference in editor.get_components(prefixes="*"):
        remaining_pin_coordinates |= collect_component_pin_coordinates(
            editor, reference=str(other_reference)
        )
    orphaned = removed_pin_coordinates - remaining_pin_coordinates
    return _remove_orphaned_connections(editor, orphaned)


def create_blank_schematic_file(
    output_path: str | Path,
    *,
    workspace_root: Path,
    overwrite: bool = False,
) -> tuple[Path, bool]:
    """Create a minimal blank `.qsch` file inside the workspace root."""

    destination = resolve_schematic_output_path(
        output_path,
        workspace_root=workspace_root.resolve(strict=False),
        default=workspace_root / "untitled.qsch",
    )
    existed = destination.exists()
    if existed and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing schematic: {destination}")

    editor_factory, backend_name = load_qsch_editor_factory()
    if editor_factory is None or backend_name is None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_blank_schematic(destination)
        return destination.resolve(strict=False), existed

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        editor = editor_factory(str(destination), create_blank=True)
    except Exception as exc:
        raise QSpiceError(
            f"Failed to create a blank schematic at {destination.name} "
            f"using {backend_name}.QschEditor."
        ) from exc

    bootstrap_blank_schematic(editor)
    editor.save_as(destination)
    if not destination.is_file():
        raise ArtifactMissingError(
            f"Blank schematic creation did not produce an artifact: {destination}"
        )
    return destination.resolve(strict=False), existed
