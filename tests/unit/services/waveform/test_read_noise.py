"""Tests for native `.noise` log parsing."""

from __future__ import annotations

from pathlib import Path
from shutil import copy2

from qspice_mcp.services.waveform.read_noise import read_noise

REPO_ROOT = Path(__file__).resolve().parents[4]
NOISE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "logs" / "noise-summary.log"


def test_read_noise_parses_summary_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "demo.log"
    copy2(NOISE_FIXTURE, log_path)

    result = read_noise(log_path, workspace_root=tmp_path)

    assert result.warnings == ()
    assert len(result.summaries) == 3
    labels = {entry.label for entry in result.summaries}
    assert "Total RMS Noise Voltage at v(out)" in labels
    assert any("Output noise" in label for label in labels)


def test_read_noise_warns_when_missing(tmp_path: Path) -> None:
    log_path = tmp_path / "empty.log"
    log_path.write_text("Transient complete\n", encoding="utf-8")

    result = read_noise(log_path, workspace_root=tmp_path)

    assert result.summaries == ()
    assert result.warnings
