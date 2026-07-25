"""Tests for topology-foldered recipe resolution and attribution."""

from __future__ import annotations

import json

from qspice_mcp.services.recipes._catalog import (
    list_recipe_index_entries,
    load_recipe_manifest,
    read_recipe_document,
    read_recipe_schematic_bytes,
    recipe_attribution,
)

# Clean-room recipes authored in this repo (no external attribution).
_CLEANROOM_RECIPE_IDS = frozenset(
    {
        "buck_converter_cpp",
        "boost_converter_cpp",
        "flyback_converter_cpp",
        "forward_converter",
        "half_bridge_converter",
        "full_bridge_converter",
    }
)
# Recipes adapted from J. Marcos Alonso's repositories (must carry source provenance).
_ALONSO_RECIPE_IDS = frozenset(
    {
        "flyback_qr",
        "buck_boost_dcm",
        "two_phase_buck",
        "llc_resonant",
        "series_resonant_src",
        "parallel_resonant_prc",
        "class_e",
        "half_bridge_zvs",
        "npc_inverter",
        "push_pull_resonant",
        "digital_pwm_cblock",
        "digital_buck_closed_loop",
        "digital_current_mode_buck",
        "pv_mppt_po",
        "voltage_fed_push_pull",
        "push_pull_uc1846",
    }
)


def test_directory_defaults_to_recipe_id_when_omitted() -> None:
    # Every shipped recipe now declares an explicit topology folder, so the
    # directory always ends with the recipe_id segment (flat or nested default).
    for entry in list_recipe_index_entries():
        assert entry.directory.split("/")[-1] == entry.recipe_id


def test_legacy_cpp_recipes_live_in_topology_folders() -> None:
    entries = {e.recipe_id: e for e in list_recipe_index_entries()}
    assert entries["buck_converter_cpp"].directory == "non_isolated_dc_dc/buck_converter_cpp"
    assert entries["boost_converter_cpp"].directory == "non_isolated_dc_dc/boost_converter_cpp"
    assert entries["flyback_converter_cpp"].directory == "isolated_dc_dc/flyback_converter_cpp"


def test_foldered_recipe_directory_is_nested() -> None:
    entries = {e.recipe_id: e for e in list_recipe_index_entries()}
    assert entries["llc_resonant"].directory == "resonant_dc_dc/llc_resonant"


def test_foldered_recipe_manifest_resolves_via_directory() -> None:
    manifest = load_recipe_manifest("llc_resonant")
    assert manifest["recipe_id"] == "llc_resonant"
    bundle_names = {f["bundle_name"] for f in manifest["files"]}
    assert "llc_resonant.cir" in bundle_names


def test_foldered_recipe_bundles_schematic_and_document() -> None:
    assert len(read_recipe_schematic_bytes("flyback_qr")) > 0
    body = read_recipe_document("class_e", "catalog.md")
    assert "materialize" in body.lower()


def test_recipe_attribution_records_alonso_permission() -> None:
    attribution = recipe_attribution()
    assert "alonso_recipes" in attribution
    assert "permission" in attribution["alonso_recipes"]


def test_every_alonso_recipe_declares_source_provenance() -> None:
    for recipe_id in _ALONSO_RECIPE_IDS:
        manifest = load_recipe_manifest(recipe_id)
        source = manifest.get("source")
        assert isinstance(source, dict), recipe_id
        for key in ("author", "repo", "path", "commit", "permission"):
            assert source.get(key), f"{recipe_id} missing source.{key}"
        # author must credit Marcos Alonso by name
        assert "alonso" in str(source["author"]).lower(), recipe_id
        # commit must look like a git SHA
        assert len(str(source["commit"])) >= 7


def test_cleanroom_recipes_have_no_external_source() -> None:
    for recipe_id in _CLEANROOM_RECIPE_IDS:
        manifest = load_recipe_manifest(recipe_id)
        assert manifest.get("source") is None, recipe_id


def test_recipe_id_sets_cover_the_index() -> None:
    known = _CLEANROOM_RECIPE_IDS | _ALONSO_RECIPE_IDS
    shipped = {entry.recipe_id for entry in list_recipe_index_entries()}
    assert shipped == known


def test_foldered_recipe_json_is_valid() -> None:
    for entry in list_recipe_index_entries():
        manifest = load_recipe_manifest(entry.recipe_id)
        # round-trips as JSON and keeps the id consistent with the index
        json.dumps(manifest)
        assert manifest["recipe_id"] == entry.recipe_id
