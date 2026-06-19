"""Validation/drift guard for the bundled agent skills catalog.

Mirrors the discipline of the tool-reference and metadata-casing guards: every
shipped skill must declare valid frontmatter and a manifest whose
``requires-tools`` map only to real registered MCP tools, and whose
``requires-skills`` resolve to other skills in the catalog.
"""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING

import pytest

from qspice_mcp.mcp.tool_registry import build_runtime_tool_registry

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable

_SKILLS_ROOT = "qspice_mcp.data.skills"


def _catalog_root() -> Traversable:
    return files(_SKILLS_ROOT)


def _iter_group_dirs() -> list[Traversable]:
    groups: list[Traversable] = []
    for entry in _catalog_root().iterdir():
        if entry.is_dir() and (entry / "plugin.yaml").is_file():
            groups.append(entry)
    return groups


def _iter_skill_dirs() -> list[Traversable]:
    skills: list[Traversable] = []
    for group in _iter_group_dirs():
        for entry in group.iterdir():
            if entry.is_dir() and (entry / "SKILL.md").is_file():
                skills.append(entry)
    return skills


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the simple ``key: value`` YAML frontmatter block of a SKILL.md."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def _parse_manifest(text: str) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Parse our controlled manifest.yaml into scalar and list sections."""

    scalars: dict[str, str] = {}
    lists: dict[str, list[str]] = {}
    current_list: str | None = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            item = line.strip()
            if current_list is not None and item.startswith("- "):
                lists[current_list].append(item[2:].strip())
            continue
        current_list = None
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value:
            scalars[key] = value
        else:
            current_list = key
            lists[key] = []
    return scalars, lists


def _registered_tool_names() -> set[str]:
    return {tool.name for tool in build_runtime_tool_registry()}


def _skill_names() -> set[str]:
    return {skill.name for skill in _iter_skill_dirs()}


def test_catalog_has_groups_and_skills() -> None:
    groups = _iter_group_dirs()
    assert groups, "expected at least one skill group with a plugin.yaml"
    assert any(group.name == "qspice-core" for group in groups)
    assert _iter_skill_dirs(), "expected at least one skill with a SKILL.md"


@pytest.mark.parametrize("skill", _iter_skill_dirs(), ids=lambda s: s.name)
def test_skill_frontmatter_is_valid(skill: Traversable) -> None:
    front = _parse_frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
    assert front.get("name") == skill.name, (
        f"{skill.name}: frontmatter name must match directory name"
    )
    assert len(front.get("description", "")) >= 30, (
        f"{skill.name}: needs a trigger-oriented description"
    )


@pytest.mark.parametrize("skill", _iter_skill_dirs(), ids=lambda s: s.name)
def test_skill_manifest_is_valid(skill: Traversable) -> None:
    manifest_file = skill / "manifest.yaml"
    assert manifest_file.is_file(), f"{skill.name}: missing manifest.yaml"
    scalars, lists = _parse_manifest(manifest_file.read_text(encoding="utf-8"))

    for key in ("schema_version", "version", "human-description"):
        assert key in scalars, f"{skill.name}: manifest missing '{key}'"
    assert "requires-tools" in lists, f"{skill.name}: manifest missing requires-tools"


@pytest.mark.parametrize("skill", _iter_skill_dirs(), ids=lambda s: s.name)
def test_skill_requires_tools_are_registered(skill: Traversable) -> None:
    _, lists = _parse_manifest((skill / "manifest.yaml").read_text(encoding="utf-8"))
    registered = _registered_tool_names()
    unknown = [tool for tool in lists.get("requires-tools", []) if tool not in registered]
    assert not unknown, f"{skill.name}: requires-tools not registered: {unknown}"


@pytest.mark.parametrize("skill", _iter_skill_dirs(), ids=lambda s: s.name)
def test_skill_requires_skills_resolve(skill: Traversable) -> None:
    _, lists = _parse_manifest((skill / "manifest.yaml").read_text(encoding="utf-8"))
    known = _skill_names()
    unknown = [dep for dep in lists.get("requires-skills", []) if dep not in known]
    assert not unknown, f"{skill.name}: requires-skills not found in catalog: {unknown}"
