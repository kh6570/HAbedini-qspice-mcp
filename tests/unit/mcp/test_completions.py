"""Tests for MCP completion handlers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.types import (
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
)

from qspice_mcp.mcp.completions.registration import (
    _complete_prompt_argument,
    _complete_recipe_template,
    _complete_workspace_artifact_template,
    resolve_completion,
)


def test_complete_recipe_id_from_manifest_template() -> None:
    completion = _complete_recipe_template(
        "recipe://{recipe_id}/manifest",
        CompletionArgument(name="recipe_id", value="buck"),
    )

    assert completion is not None
    assert "buck_converter_cpp" in completion.values


def test_complete_recipe_document_when_recipe_id_in_context() -> None:
    completion = _complete_recipe_template(
        "recipe://{recipe_id}/{document}",
        CompletionArgument(name="document", value="cat"),
        context=CompletionContext(arguments={"recipe_id": "buck_converter_cpp"}),
    )

    assert completion is not None
    assert "catalog.md" in completion.values


def test_complete_instruction_id_for_prompts() -> None:
    completion = _complete_prompt_argument(
        "qspice_buck_converter_from_scratch",
        CompletionArgument(name="instruction_id", value="buck"),
        workspace_root=Path(),
    )

    assert completion is not None
    assert any(value.startswith("buck-converter") for value in completion.values)


def test_complete_workspace_artifact_relpath(tmp_path: Path) -> None:
    artifact = tmp_path / "runs" / "demo.qraw"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"demo")

    completion = _complete_workspace_artifact_template(
        CompletionArgument(name="relpath", value="runs~"),
        workspace_root=tmp_path,
    )

    assert completion is not None
    assert "runs~demo.qraw" in completion.values


@pytest.mark.anyio
async def test_resolve_completion_routes_recipe_template() -> None:
    completion = await resolve_completion(
        ResourceTemplateReference(type="ref/resource", uri="recipe://{recipe_id}/manifest"),
        CompletionArgument(name="recipe_id", value=""),
        None,
        workspace_root=Path(),
    )

    assert completion is not None
    assert completion.values


@pytest.mark.anyio
async def test_resolve_completion_routes_reference_template() -> None:
    completion = await resolve_completion(
        ResourceTemplateReference(type="ref/resource", uri="reference://{document}"),
        CompletionArgument(name="document", value="dir"),
        None,
        workspace_root=Path(),
    )

    assert completion is not None
    assert "directives" in completion.values


@pytest.mark.anyio
async def test_resolve_completion_routes_workspace_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "demo.qraw"
    artifact.write_bytes(b"x")

    completion = await resolve_completion(
        ResourceTemplateReference(type="ref/resource", uri="workspace-artifact://{relpath}"),
        CompletionArgument(name="relpath", value="demo"),
        None,
        workspace_root=tmp_path,
    )

    assert completion is not None
    assert "demo.qraw" in completion.values


def test_complete_recipe_document_without_context_returns_empty() -> None:
    completion = _complete_recipe_template(
        "recipe://{recipe_id}/{document}",
        CompletionArgument(name="document", value="cat"),
    )

    assert completion is not None
    assert completion.values == []


def test_complete_signal_with_raw_path_context(monkeypatch, tmp_path: Path) -> None:
    def fake_list_signals(raw_path: str, *, workspace_root: Path) -> SimpleNamespace:
        del raw_path, workspace_root
        return SimpleNamespace(
            signals=(
                SimpleNamespace(name="V(out)"),
                SimpleNamespace(name="I(L1)"),
            )
        )

    monkeypatch.setattr(
        "qspice_mcp.mcp.completions.registration.list_signals",
        fake_list_signals,
    )

    completion = _complete_prompt_argument(
        "qspice_waveform_summary",
        CompletionArgument(name="signal", value="V("),
        workspace_root=tmp_path,
        context=CompletionContext(arguments={"raw_path": "demo.qraw"}),
    )

    assert completion is not None
    assert completion.values == ["V(out)"]


@pytest.mark.anyio
async def test_resolve_completion_routes_prompt_reference() -> None:
    completion = await resolve_completion(
        PromptReference(type="ref/prompt", name="qspice_buck_converter_from_scratch"),
        CompletionArgument(name="instruction_id", value="buck"),
        None,
        workspace_root=Path(),
    )

    assert completion is not None
    assert any(value.startswith("buck-converter") for value in completion.values)
