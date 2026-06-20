"""Tests for ServiceSpec annotation drift guard."""

from __future__ import annotations

from scripts.check_service_spec_annotation_drift import collect_annotation_drift_issues


def test_collect_annotation_drift_issues_is_clean() -> None:
    assert collect_annotation_drift_issues() == []
