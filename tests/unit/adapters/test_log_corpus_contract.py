"""Adapter contract tests pinned to a real local QSpice log corpus.

These read committed `.log` fixtures captured from QSpice build ``20260604`` and
assert the ``cli.v1`` classifier maps them to the right outcome. No QSpice
executable is required, so they run in the standard (non-integration) gate.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from qspice_mcp.adapters.cli import qspice_v1
from qspice_mcp.adapters.cli.qspice_v1 import CurrentQSpiceCLIAdapter, resolve_log_rules
from qspice_mcp.core.exceptions import ConvergenceError, SimulationError

pytestmark = pytest.mark.contract

_CORPUS_VERSION = "20260604"
_CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "qspice_logs"


def _read_log(name: str) -> str:
    return (_CORPUS_DIR / name).read_text(encoding="utf-8")


def test_real_healthy_log_classifies_as_success() -> None:
    adapter = CurrentQSpiceCLIAdapter()
    result = adapter.classify_simulation_log(
        _read_log("healthy.log"),
        exit_code=0,
        probe_version=_CORPUS_VERSION,
    )
    assert result is None


def test_real_fatal_log_classifies_as_fatal_simulation_error() -> None:
    adapter = CurrentQSpiceCLIAdapter()
    result = adapter.classify_simulation_log(
        _read_log("fatal.log"),
        exit_code=1,
        probe_version=_CORPUS_VERSION,
    )
    assert isinstance(result, SimulationError)
    assert not isinstance(result, ConvergenceError)


def test_real_recovered_singular_warning_is_not_a_failure() -> None:
    adapter = CurrentQSpiceCLIAdapter()
    result = adapter.classify_simulation_log(
        _read_log("singular.log"),
        exit_code=0,
        probe_version=_CORPUS_VERSION,
    )
    assert result is None


def test_resolve_log_rules_falls_back_to_base_for_unknown_version() -> None:
    base = resolve_log_rules(None)
    unknown = resolve_log_rules("19990101")
    assert unknown == base


def test_resolve_log_rules_returns_registered_version_entry() -> None:
    rules = resolve_log_rules(_CORPUS_VERSION)
    assert rules.convergence == qspice_v1._BASE_LOG_RULES.convergence
    assert rules.ignore == qspice_v1._BASE_LOG_RULES.ignore


_V2_CORPUS_VERSION = "20271231"
_V2_CORPUS_DIR = _CORPUS_DIR / "v2_20271231"


def _read_v2_log(name: str) -> str:
    return (_V2_CORPUS_DIR / name).read_text(encoding="utf-8")


def test_synthetic_second_build_healthy_log_is_success() -> None:
    adapter = CurrentQSpiceCLIAdapter()
    assert (
        adapter.classify_simulation_log(
            _read_v2_log("healthy.log"), exit_code=0, probe_version=_V2_CORPUS_VERSION
        )
        is None
    )


def test_synthetic_second_build_convergence_log_diverges_from_base() -> None:
    adapter = CurrentQSpiceCLIAdapter()
    log_text = _read_v2_log("convergence.log")
    # The base/real-build rules do not recognize this build's signature.
    assert adapter.classify_simulation_log(log_text, exit_code=1, probe_version=None) is None
    assert (
        adapter.classify_simulation_log(log_text, exit_code=1, probe_version=_CORPUS_VERSION)
        is None
    )
    # The second build classifies it as a convergence failure.
    classified = adapter.classify_simulation_log(
        log_text, exit_code=1, probe_version=_V2_CORPUS_VERSION
    )
    assert isinstance(classified, ConvergenceError)


def test_synthetic_second_build_fatal_log_diverges_from_base() -> None:
    adapter = CurrentQSpiceCLIAdapter()
    log_text = _read_v2_log("fatal.log")
    assert adapter.classify_simulation_log(log_text, exit_code=1, probe_version=None) is None
    classified = adapter.classify_simulation_log(
        log_text, exit_code=1, probe_version=_V2_CORPUS_VERSION
    )
    assert isinstance(classified, SimulationError)
    assert not isinstance(classified, ConvergenceError)


def test_resolve_log_rules_normalizes_dotted_version() -> None:
    assert resolve_log_rules("2026.06.04") == resolve_log_rules(_CORPUS_VERSION)


def test_version_override_seam_adds_build_specific_fatal_signature(monkeypatch) -> None:
    fake_version = "29991231"
    monkeypatch.setitem(
        qspice_v1._VERSION_LOG_OVERRIDES,
        fake_version,
        qspice_v1._LogRuleOverride(
            extra_fatal=(re.compile(r"\bquantum flux desync\b", re.IGNORECASE),)
        ),
    )
    adapter = CurrentQSpiceCLIAdapter()

    # Unknown to the base rules, but matched once the version override applies.
    assert (
        adapter.classify_simulation_log("Quantum flux desync at node Z", probe_version=None) is None
    )
    classified = adapter.classify_simulation_log(
        "Quantum flux desync at node Z",
        exit_code=1,
        probe_version=fake_version,
    )
    assert isinstance(classified, SimulationError)
