"""Unit tests for the topology knowledge-pack services."""

from __future__ import annotations

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.topology._catalog import load_topology_manifest
from qspice_mcp.services.topology.describe_topology_block import describe_topology_block
from qspice_mcp.services.topology.list_topology_blocks import list_topology_blocks
from qspice_mcp.services.topology.search_topology_blocks import search_topology_blocks
from qspice_mcp.services.topology.validate_topology_contribution import (
    validate_topology_contribution,
)

_EXPECTED_BLOCK_IDS = {
    "buck_converter",
    "boost_converter",
    "buck_boost_converter",
    "flyback_converter",
    "forward_converter",
    "half_bridge_converter",
}


def test_list_topology_blocks_returns_all_blocks_with_attribution() -> None:
    catalog = list_topology_blocks()
    assert {block.block_id for block in catalog.blocks} == _EXPECTED_BLOCK_IDS
    assert catalog.attribution["primary_reference"]["author"] == "J. Marcos Alonso"


def test_describe_topology_block_includes_equations_and_document() -> None:
    detail = describe_topology_block("boost_converter")
    assert detail.block_id == "boost_converter"
    equation_names = {equation["name"] for equation in detail.design_equations}
    assert "conversion_ratio" in equation_names
    assert "rhp_zero" in equation_names
    assert detail.document_name == "blueprint.md"
    assert "Boost converter" in detail.document
    assert detail.reference["isbn"] == "979-8278321743"


def test_describe_topology_block_rejects_unknown_block() -> None:
    with pytest.raises(ValidationError, match="Unknown topology block_id"):
        describe_topology_block("flyback")


def test_search_ranks_boost_for_step_up_keywords() -> None:
    result = search_topology_blocks("step up rhp")
    assert result.matches
    assert result.matches[0].block_id == "boost_converter"
    assert result.matches[0].score > 0.0
    assert all(match.matched_terms for match in result.matches)


def test_search_matches_blueprint_only_term() -> None:
    """A term that appears only in the blueprint document still retrieves the block."""

    result = search_topology_blocks("inrush")
    block_ids = {match.block_id for match in result.matches}
    assert "boost_converter" in block_ids
    boost_match = next(match for match in result.matches if match.block_id == "boost_converter")
    assert boost_match.score > 0.0
    assert "inrush" in boost_match.matched_terms
    assert "blueprint" in boost_match.matched_fields


def test_search_respects_limit() -> None:
    result = search_topology_blocks("converter", limit=1)
    assert len(result.matches) == 1


def test_search_matches_buck_boost_on_inverting() -> None:
    # The flyback is also described as an inverting buck-boost derivative, so "inverting"
    # legitimately retrieves both; assert the buck-boost block is still found.
    result = search_topology_blocks("inverting")
    assert "buck_boost_converter" in {match.block_id for match in result.matches}


def test_buck_manifest_includes_ccm_dcm_and_small_signal_equations() -> None:
    detail = describe_topology_block("buck_converter")
    equation_names = {equation["name"] for equation in detail.design_equations}
    assert {
        "conversion_ratio",
        "conversion_ratio_with_losses",
        "boundary_load_resistance",
        "dcm_conversion_ratio",
        "ccm_characteristic_polynomial",
        "control_to_output_tf_ccm",
        "output_impedance_tf_ccm",
        "input_impedance_tf_ccm",
    } <= equation_names
    # The enriched manifest must still satisfy the pack schema validator.
    outcome = validate_topology_contribution(load_topology_manifest("buck_converter"))
    assert outcome.is_valid, outcome.errors


def test_boost_manifest_includes_ccm_dcm_and_small_signal_equations() -> None:
    detail = describe_topology_block("boost_converter")
    equation_names = {equation["name"] for equation in detail.design_equations}
    assert {
        "conversion_ratio",
        "conversion_ratio_with_losses",
        "rhp_zero",
        "boundary_load_resistance",
        "dcm_conversion_ratio",
        "ccm_characteristic_polynomial",
        "control_to_output_tf_ccm",
        "output_impedance_tf_ccm",
        "input_impedance_tf_ccm",
    } <= equation_names
    outcome = validate_topology_contribution(load_topology_manifest("boost_converter"))
    assert outcome.is_valid, outcome.errors


def test_buck_boost_manifest_includes_ccm_dcm_and_small_signal_equations() -> None:
    detail = describe_topology_block("buck_boost_converter")
    equation_names = {equation["name"] for equation in detail.design_equations}
    assert {
        "conversion_ratio",
        "conversion_ratio_with_losses",
        "rhp_zero",
        "boundary_load_resistance",
        "dcm_conversion_ratio",
        "ccm_characteristic_polynomial",
        "control_to_output_tf_ccm",
        "audio_susceptibility_tf_ccm",
        "output_impedance_tf_ccm",
        "input_impedance_tf_ccm",
    } <= equation_names
    outcome = validate_topology_contribution(load_topology_manifest("buck_boost_converter"))
    assert outcome.is_valid, outcome.errors


def test_flyback_manifest_includes_isolation_ccm_dcm_and_small_signal_equations() -> None:
    detail = describe_topology_block("flyback_converter")
    assert detail.category == "isolated_dc_dc"
    equation_names = {equation["name"] for equation in detail.design_equations}
    assert {
        "turns_ratio",
        "conversion_ratio",
        "rhp_zero",
        "boundary_load_resistance",
        "dcm_conversion_ratio",
        "ccm_characteristic_polynomial",
        "control_to_output_tf_ccm",
        "audio_susceptibility_tf_ccm",
        "output_impedance_tf_ccm",
        "input_impedance_tf_ccm",
    } <= equation_names
    outcome = validate_topology_contribution(load_topology_manifest("flyback_converter"))
    assert outcome.is_valid, outcome.errors


def test_search_matches_flyback_on_isolation_terms() -> None:
    # "flyback" and "coupled-inductor" are most concentrated in the flyback block (the
    # forward block only mentions flyback in passing), so it should rank first.
    result = search_topology_blocks("flyback coupled-inductor isolated")
    assert result.matches
    assert result.matches[0].block_id == "flyback_converter"
    assert result.matches[0].score > 0.0


def test_forward_manifest_includes_isolation_ccm_dcm_and_small_signal_equations() -> None:
    detail = describe_topology_block("forward_converter")
    assert detail.category == "isolated_dc_dc"
    equation_names = {equation["name"] for equation in detail.design_equations}
    assert {
        "conversion_ratio",
        "demagnetization_constraint",
        "boundary_load_resistance",
        "dcm_conversion_ratio",
        "ccm_characteristic_polynomial",
        "control_to_output_tf_ccm",
        "audio_susceptibility_tf_ccm",
        "output_impedance_tf_ccm",
        "input_impedance_tf_ccm",
    } <= equation_names
    # The forward is buck-derived: its control-to-output plant has no right-half-plane zero.
    assert "rhp_zero" not in equation_names
    outcome = validate_topology_contribution(load_topology_manifest("forward_converter"))
    assert outcome.is_valid, outcome.errors


def test_search_matches_forward_on_reset_winding_terms() -> None:
    result = search_topology_blocks("forward reset winding demagnetization")
    assert result.matches
    assert result.matches[0].block_id == "forward_converter"
    assert result.matches[0].score > 0.0


def test_half_bridge_manifest_includes_isolation_ccm_dcm_and_small_signal_equations() -> None:
    detail = describe_topology_block("half_bridge_converter")
    assert detail.category == "isolated_dc_dc"
    equation_names = {equation["name"] for equation in detail.design_equations}
    assert {
        "turns_ratio",
        "conversion_ratio",
        "boundary_load_resistance",
        "dcm_conversion_ratio",
        "ccm_characteristic_polynomial",
        "control_to_output_tf_ccm",
        "audio_susceptibility_tf_ccm",
        "output_impedance_tf_ccm",
        "input_impedance_tf_ccm",
    } <= equation_names
    # The half-bridge is buck-derived: its control-to-output plant has no right-half-plane zero.
    assert "rhp_zero" not in equation_names
    outcome = validate_topology_contribution(load_topology_manifest("half_bridge_converter"))
    assert outcome.is_valid, outcome.errors


def test_search_matches_half_bridge_on_topology_terms() -> None:
    result = search_topology_blocks("half-bridge totem-pole input-capacitor divider")
    assert result.matches
    assert result.matches[0].block_id == "half_bridge_converter"
    assert result.matches[0].score > 0.0


def test_search_retrieves_enriched_blocks_for_small_signal_terms() -> None:
    """Small-signal terms added to buck and boost retrieve both enriched blocks."""

    result = search_topology_blocks("discontinuous conduction audio susceptibility")
    block_ids = {match.block_id for match in result.matches}
    assert {"buck_converter", "boost_converter"} <= block_ids
    assert all(match.score > 0.0 for match in result.matches)


def test_search_rejects_empty_query() -> None:
    with pytest.raises(ValidationError, match="must not be empty"):
        search_topology_blocks("   ")


def test_search_with_no_match_returns_empty() -> None:
    result = search_topology_blocks("piezoelectric photovoltaic magnetron")
    assert result.matches == ()


@pytest.mark.parametrize("block_id", sorted(_EXPECTED_BLOCK_IDS))
def test_bundled_manifests_pass_their_own_validator(block_id: str) -> None:
    manifest = load_topology_manifest(block_id)
    outcome = validate_topology_contribution(manifest)
    assert outcome.is_valid, outcome.errors
    assert outcome.block_id == block_id
    assert outcome.errors == ()


def test_validate_reports_missing_required_fields() -> None:
    outcome = validate_topology_contribution({"block_id": "demo"})
    assert outcome.is_valid is False
    assert outcome.block_id == "demo"
    joined = " ".join(outcome.errors)
    assert "'title'" in joined
    assert "'tags'" in joined
    assert "'ports'" in joined
    assert "'reference'" in joined


def test_validate_rejects_non_object_manifest() -> None:
    outcome = validate_topology_contribution(["not", "a", "manifest"])  # type: ignore[arg-type]
    assert outcome.is_valid is False
    assert outcome.block_id is None
    assert outcome.errors == ("manifest must be a JSON object.",)


def test_validate_flags_bad_block_id_characters() -> None:
    manifest = dict(load_topology_manifest("buck_converter"))
    manifest["block_id"] = "bad id!"
    outcome = validate_topology_contribution(manifest)
    assert outcome.is_valid is False
    assert any("alphanumeric" in error for error in outcome.errors)


def test_validate_warns_when_reference_lacks_traceability() -> None:
    manifest = dict(load_topology_manifest("buck_converter"))
    manifest["reference"] = {"source": "Some textbook"}
    outcome = validate_topology_contribution(manifest)
    assert outcome.is_valid is True
    assert any("url" in warning or "isbn" in warning for warning in outcome.warnings)
