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
    assert buck.topology_block == "buck_converter"
    assert "buck" in buck.tags


def test_list_reference_circuit_recipes_exposes_topology_blocks_and_tags() -> None:
    result = list_reference_circuit_recipes()

    by_id = {entry.recipe_id: entry for entry in result.recipes}
    # Every bundled recipe declares tags.
    assert all(entry.tags for entry in result.recipes)
    assert by_id["boost_converter_cpp"].topology_block == "boost_converter"
    assert by_id["flyback_converter_cpp"].topology_block == "flyback_converter"
    assert by_id["half_bridge_zvs"].topology_block == "half_bridge_converter"
    # Recipes without a matching topology-pack entry link to nothing.
    assert by_id["llc_resonant"].topology_block is None
    assert "resonant" in by_id["llc_resonant"].tags


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


def test_describe_recipe_surfaces_topology_block_link_and_tags() -> None:
    result = describe_reference_circuit_recipe("buck_converter_cpp")

    assert result.topology_block == "buck_converter"
    assert result.topology_block_note is None
    assert "mixed-signal" in result.tags


def test_describe_half_bridge_zvs_carries_topology_block_note() -> None:
    result = describe_reference_circuit_recipe("half_bridge_zvs")

    assert result.topology_block == "half_bridge_converter"
    assert result.topology_block_note is not None
    assert "ZVS" in result.topology_block_note


def test_new_isolated_converter_recipes_are_listed_with_topology_links() -> None:
    result = list_reference_circuit_recipes()

    by_id = {entry.recipe_id: entry for entry in result.recipes}
    for recipe_id in ("forward_converter", "half_bridge_converter", "full_bridge_converter"):
        assert recipe_id in by_id, recipe_id
        assert by_id[recipe_id].topology_block == recipe_id
        assert "isolated" in by_id[recipe_id].tags


def test_describe_forward_converter_recipe_bundles_validated_netlist() -> None:
    result = describe_reference_circuit_recipe("forward_converter")

    assert result.source is None
    assert result.build_required is False
    assert {entry.relative_path for entry in result.files} == {
        "forward_converter.qsch",
        "forward_converter.cir",
    }
    instruction_ids = {entry.instruction_id for entry in result.workflows}
    assert instruction_ids == {"forward-converter-catalog"}
    assert result.topology_digest is not None
    refdes = {component.refdes for component in result.topology_digest.components}
    assert {"M1", "L2", "L3", "L4"} <= refdes


def test_describe_alonso_recipe_surfaces_source_attribution() -> None:
    result = describe_reference_circuit_recipe("flyback_qr")

    assert result.source is not None
    assert "alonso" in result.source.author.lower()
    assert result.source.repo
    assert result.source.commit
    assert result.source.permission


def test_describe_cleanroom_recipe_has_no_source() -> None:
    result = describe_reference_circuit_recipe("buck_converter_cpp")

    assert result.source is None


def test_describe_reference_circuit_recipe_rejects_unknown_id() -> None:
    with pytest.raises(ValidationError, match="Unknown recipe_id"):
        describe_reference_circuit_recipe("not-a-recipe")


def test_describe_boost_converter_recipe_uses_boost_bundle_files() -> None:
    result = describe_reference_circuit_recipe("boost_converter_cpp")

    assert result.recipe_id == "boost_converter_cpp"
    assert result.build_required is False
    assert result.build_hint is not None
    assert 'build_dll_device(source_path="boost_controller.cpp")' in result.build_hint
    assert {entry.relative_path for entry in result.files} == {
        "Boost-converter.qsch",
        "boost_controller.cpp",
        "boost_controller.dll",
    }
    assert result.topology_digest is not None
    assert result.topology_digest.schematic_file == "Boost-converter.qsch"
    x1 = next(
        component for component in result.topology_digest.components if component.refdes == "X1"
    )
    assert ".dll" in x1.kind.lower()
