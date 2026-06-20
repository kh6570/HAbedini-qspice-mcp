"""Tests for bundled reference-circuit recipe discovery services."""

from __future__ import annotations

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.recipes.describe_reference_circuit_recipe import (
    describe_reference_circuit_recipe,
)
from qspice_mcp.services.recipes.list_reference_circuit_recipes import (
    list_reference_circuit_recipes,
)


def test_list_reference_circuit_recipes_includes_buck_converter() -> None:
    result = list_reference_circuit_recipes()

    assert result.discovery_guidance
    assert "list_reference_circuit_recipes" in result.discovery_guidance

    recipe_ids = {entry.recipe_id for entry in result.recipes}
    assert "buck_converter_cpp" in recipe_ids
    assert "boost_converter_cpp" in recipe_ids

    buck = next(entry for entry in result.recipes if entry.recipe_id == "buck_converter_cpp")
    assert buck.title == "Buck Converter (C++ DLL)"
    assert buck.summary is not None
    assert "PWM" in buck.summary


def test_describe_reference_circuit_recipe_returns_manifest_and_topology() -> None:
    result = describe_reference_circuit_recipe("buck_converter_cpp")

    assert result.recipe_id == "buck_converter_cpp"
    assert result.discovery_guidance
    assert result.build_required is True
    assert result.build_hint == 'build_dll_device(source_path="buck_controller.cpp")'
    assert len(result.files) == 2
    assert {entry.relative_path for entry in result.files} == {
        "Buck-converter.qsch",
        "buck_controller.cpp",
    }

    instruction_ids = {entry.instruction_id for entry in result.workflows}
    assert instruction_ids == {"buck-converter-cpp", "buck-converter-cpp-catalog"}
    catalog = next(
        entry for entry in result.workflows if entry.instruction_id == "buck-converter-cpp-catalog"
    )
    assert catalog.track == "reference_catalog"
    assert catalog.document == "catalog.md"

    assert result.topology_digest is not None
    digest = result.topology_digest
    assert digest.schematic_file == "Buck-converter.qsch"
    assert digest.component_count > 0
    refdes = {component.refdes for component in digest.components}
    assert "X1" in refdes
    x1 = next(component for component in digest.components if component.refdes == "X1")
    assert ".dll" in x1.kind.lower()
    assert any(analysis.lower().startswith(".tran") for analysis in digest.analyses)
    assert digest.size_bytes > 0


def test_describe_reference_circuit_recipe_rejects_unknown_id() -> None:
    with pytest.raises(ValidationError, match="Unknown recipe_id"):
        describe_reference_circuit_recipe("not-a-recipe")


def test_describe_boost_converter_recipe_uses_boost_bundle_files() -> None:
    result = describe_reference_circuit_recipe("boost_converter_cpp")

    assert result.recipe_id == "boost_converter_cpp"
    assert result.build_hint == 'build_dll_device(source_path="boost_controller.cpp")'
    assert {entry.relative_path for entry in result.files} == {
        "Boost-converter.qsch",
        "boost_controller.cpp",
    }
    assert result.topology_digest is not None
    assert result.topology_digest.schematic_file == "Boost-converter.qsch"
    x1 = next(
        component for component in result.topology_digest.components if component.refdes == "X1"
    )
    assert ".dll" in x1.kind.lower()
