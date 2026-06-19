"""Tests for native `.four` log parsing."""

from __future__ import annotations

from pathlib import Path
from shutil import copy2

import pytest

from qspice_mcp.services.waveform.read_fourier import read_fourier

REPO_ROOT = Path(__file__).resolve().parents[4]
FOURIER_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "logs" / "fourier-four.log"


def test_read_fourier_parses_harmonics(tmp_path: Path) -> None:
    log_path = tmp_path / "demo.log"
    copy2(FOURIER_FIXTURE, log_path)

    result = read_fourier(log_path, workspace_root=tmp_path)

    assert result.warnings == ()
    assert len(result.analyses) == 1
    analysis = result.analyses[0]
    assert analysis.node == "V(out)"
    assert analysis.dc_component == 5.0
    assert analysis.total_harmonic_distortion_pct == pytest.approx(5.0)
    assert len(analysis.harmonics) == 2
    assert analysis.harmonics[0].harmonic == 1
    assert analysis.harmonics[0].frequency_hz == pytest.approx(1000.0)


def test_read_fourier_warns_when_missing(tmp_path: Path) -> None:
    log_path = tmp_path / "empty.log"
    log_path.write_text("Transient complete\n", encoding="utf-8")

    result = read_fourier(log_path, workspace_root=tmp_path)

    assert result.analyses == ()
    assert result.warnings
