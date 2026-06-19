"""Completion providers for MCP prompts and resource templates."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from mcp.types import Completion, PromptReference, ResourceTemplateReference

from qspice_mcp.services.instructions._catalog import list_workflow_instruction_entries
from qspice_mcp.services.recipes._catalog import list_recipe_index_entries, load_recipe_manifest
from qspice_mcp.services.waveform.list_signals import list_signals

if TYPE_CHECKING:
    from pathlib import Path

    from mcp.server.fastmcp import FastMCP
    from mcp.types import CompletionArgument, CompletionContext

_MAX_COMPLETIONS = 100
_RECIPE_URI_PREFIX = "recipe://"
_WORKSPACE_ARTIFACT_URI_PREFIX = "workspace-artifact://"


def _filter_prefix(values: tuple[str, ...] | list[str], partial: str) -> list[str]:
    normalized_partial = partial.strip().lower()
    if not normalized_partial:
        return list(values[:_MAX_COMPLETIONS])
    filtered = [value for value in values if value.lower().startswith(normalized_partial)]
    return filtered[:_MAX_COMPLETIONS]


def _recipe_document_names(recipe_id: str) -> tuple[str, ...]:
    manifest = load_recipe_manifest(recipe_id)
    documents: set[str] = set()
    for key in ("catalog_document", "scratch_document"):
        raw_value = manifest.get(key)
        if isinstance(raw_value, str) and raw_value.strip():
            documents.add(raw_value.strip())
    for instruction in manifest.get("workflows", []):
        if isinstance(instruction, dict):
            document = instruction.get("document")
            if isinstance(document, str) and document.strip():
                documents.add(document.strip())
    return tuple(sorted(documents))


def _complete_recipe_template(
    uri: str,
    argument: CompletionArgument,
    *,
    context: CompletionContext | None = None,
) -> Completion | None:
    match = re.fullmatch(r"recipe://\{recipe_id\}/(\{document\}|manifest|schematic)", uri)
    if match is None:
        return None

    if argument.name == "recipe_id":
        values = _filter_prefix(
            [entry.recipe_id for entry in list_recipe_index_entries()],
            argument.value,
        )
        return Completion(values=values, total=len(values))

    if argument.name != "document" or match.group(1) != "{document}":
        return None

    recipe_id = None
    if context is not None and context.arguments is not None:
        recipe_id = context.arguments.get("recipe_id")
    if not recipe_id:
        return Completion(values=[])

    values = _filter_prefix(_recipe_document_names(recipe_id), argument.value)
    return Completion(values=values, total=len(values))


def _complete_workspace_artifact_template(
    argument: CompletionArgument,
    *,
    workspace_root: Path,
) -> Completion | None:
    if argument.name != "relpath":
        return None

    normalized_partial = argument.value.strip().lower()
    if not normalized_partial:
        return Completion(values=[])

    root = workspace_root.resolve(strict=False)
    if not root.is_dir():
        return Completion(values=[])

    artifact_suffixes = (".qsch", ".net", ".cir", ".log", ".qraw", ".csv", ".json", ".md")
    matches: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in artifact_suffixes:
            continue
        relpath = path.relative_to(root).as_posix()
        encoded = relpath.replace("/", "~")
        if encoded.lower().startswith(normalized_partial):
            matches.append(encoded)
        if len(matches) >= _MAX_COMPLETIONS:
            break
    return Completion(values=matches, total=len(matches))


def _complete_prompt_argument(
    prompt_name: str,
    argument: CompletionArgument,
    *,
    workspace_root: Path,
    context: CompletionContext | None = None,
) -> Completion | None:
    if argument.name == "instruction_id":
        values = _filter_prefix(
            [entry.instruction_id for entry in list_workflow_instruction_entries()],
            argument.value,
        )
        return Completion(values=values, total=len(values))

    if argument.name == "recipe_id":
        values = _filter_prefix(
            [entry.recipe_id for entry in list_recipe_index_entries()],
            argument.value,
        )
        return Completion(values=values, total=len(values))

    if argument.name == "signal" and context is not None and context.arguments is not None:
        raw_path = context.arguments.get("raw_path")
        if raw_path:
            try:
                catalog = list_signals(raw_path, workspace_root=workspace_root)
            except (OSError, ValueError):
                return Completion(values=[])
            values = _filter_prefix([signal.name for signal in catalog.signals], argument.value)
            return Completion(values=values, total=len(values))

    del prompt_name
    return None


async def resolve_completion(
    ref: ResourceTemplateReference | PromptReference | object,
    argument: CompletionArgument,
    context: CompletionContext | None,
    *,
    workspace_root: Path,
) -> Completion | None:
    """Route one MCP completion request to the appropriate provider."""

    if isinstance(ref, ResourceTemplateReference):
        if ref.uri.startswith(_RECIPE_URI_PREFIX):
            return _complete_recipe_template(ref.uri, argument, context=context)
        if ref.uri.startswith(_WORKSPACE_ARTIFACT_URI_PREFIX):
            return _complete_workspace_artifact_template(
                argument,
                workspace_root=workspace_root,
            )
        return None

    if isinstance(ref, PromptReference):
        return _complete_prompt_argument(
            ref.name,
            argument,
            workspace_root=workspace_root,
            context=context,
        )
    return None


def register_completions(app: FastMCP, *, workspace_root: Path) -> None:
    """Bind MCP completion handlers for prompts and resource templates."""

    @app.completion()  # type: ignore[no-untyped-call]
    async def handle_completion(ref, argument, context):  # type: ignore[no-untyped-def]
        return await resolve_completion(
            ref,
            argument,
            context,
            workspace_root=workspace_root,
        )


__all__ = ["register_completions", "resolve_completion"]
