"""Tests for bundled workflow instruction services."""

from __future__ import annotations

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.instructions.list_workflow_instructions import list_workflow_instructions
from qspice_mcp.services.instructions.read_workflow_instruction import read_workflow_instruction


def test_list_workflow_instructions_includes_buck_converter() -> None:
    result = list_workflow_instructions()

    instruction_ids = {entry.instruction_id for entry in result.instructions}
    assert "buck-converter-cpp" in instruction_ids
    assert "buck-converter-cpp-catalog" in instruction_ids


def test_read_workflow_instruction_returns_scratch_build_doc() -> None:
    result = read_workflow_instruction("buck-converter-cpp")

    assert result.instruction_id == "buck-converter-cpp"
    assert result.track == "scratch_authoring"
    assert "add_wire" in result.content
    assert ".tran 0 300µ 0 100n uic" in result.content
    assert "BSC123N08NS3" in result.content
    assert "buck_controller" in result.content


def test_read_workflow_instruction_returns_catalog_doc() -> None:
    result = read_workflow_instruction("buck-converter-cpp-catalog")

    assert result.track == "reference_catalog"
    assert result.recipe_id == "buck_converter_cpp"
    assert result.related_instruction_id == "buck-converter-cpp"
    assert "materialize_reference_circuit" in result.content


def test_read_workflow_instruction_rejects_unknown_id() -> None:
    with pytest.raises(ValidationError, match="Unknown instruction_id"):
        read_workflow_instruction("not-a-recipe")
