"""Tests for protocol co-simulation scaffold services."""

from __future__ import annotations

import pytest

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.services.protocol.describe_protocol_support import (
    describe_protocol_support,
)
from qspice_mcp.services.protocol.scaffold_i2c_device import scaffold_i2c_device
from qspice_mcp.services.protocol.scaffold_spi_device import scaffold_spi_device

# ---------------------------------------------------------------------------
# describe_protocol_support
# ---------------------------------------------------------------------------


def test_describe_protocol_support_returns_all_true(tmp_path) -> None:
    settings = QSpiceSettings(exe=tmp_path / "QSPICE64.exe", workspace_root=tmp_path)

    result = describe_protocol_support(settings=settings)

    assert result.i2c_device_scaffolding is True
    assert result.spi_device_scaffolding is True
    assert any("scaffold_i2c_device" in note for note in result.notes)
    assert any("scaffold_spi_device" in note for note in result.notes)


# ---------------------------------------------------------------------------
# scaffold_i2c_device
# ---------------------------------------------------------------------------


def test_scaffold_i2c_device_writes_dll_source(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = scaffold_i2c_device(
        "I2C_Sensor",
        workspace_root=workspace,
        settings=None,
    )

    assert result.device_name == "I2C_Sensor"
    assert result.source_path.suffix == ".cpp"
    assert result.source_path.is_file()
    assert result.line_count > 30

    text = result.source_path.read_text(encoding="utf-8")
    assert "I2C_Sensor" in text
    # I2C helpers must appear
    assert "qspice_i2c_write" in text
    assert "qspice_i2c_read" in text
    assert "qspice_i2c_start" in text
    assert "qspice_i2c_stop" in text
    assert "qspice_i2c_ack" in text
    assert "qspice_i2c_nack" in text
    # Entry points
    assert "dll_device_count" in text
    assert "dll_device(" in text
    # Pin mapping comments
    assert "SDA" in text
    assert "SCL" in text

    assert any("cl /LD" in note for note in result.notes)
    assert any("QSpice" in note for note in result.notes)


def test_scaffold_i2c_device_rejects_numeric_start(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(ValueError, match="device_name must start with a letter"):
        scaffold_i2c_device("42Device", workspace_root=workspace, settings=None)


def test_scaffold_i2c_device_custom_output_path(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = scaffold_i2c_device(
        "TempSensor",
        workspace_root=workspace,
        settings=None,
        output_path="i2c/temp.cpp",
    )

    assert result.source_path.name == "temp.cpp"
    assert result.source_path.is_file()
    assert "TempSensor" in result.source_path.read_text(encoding="utf-8")


def test_scaffold_i2c_device_accepts_underscore_name(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = scaffold_i2c_device(
        "I2C_Slave_1",
        workspace_root=workspace,
        settings=None,
    )

    assert result.source_path.is_file()
    assert "I2C_Slave_1" in result.source_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# scaffold_spi_device
# ---------------------------------------------------------------------------


def test_scaffold_spi_device_writes_dll_source(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = scaffold_spi_device(
        "SPI_Flash",
        workspace_root=workspace,
        settings=None,
    )

    assert result.device_name == "SPI_Flash"
    assert result.source_path.suffix == ".cpp"
    assert result.source_path.is_file()
    assert result.line_count > 25

    text = result.source_path.read_text(encoding="utf-8")
    assert "SPI_Flash" in text
    # SPI helpers must appear
    assert "qspice_spi_write" in text
    assert "qspice_spi_read" in text
    # Entry points
    assert "dll_device_count" in text
    assert "dll_device(" in text
    # Pin mapping comments
    assert "MOSI" in text
    assert "MISO" in text
    assert "SCLK" in text
    assert "CS" in text
    # SPI mode documentation
    assert "CPOL" in text
    assert "CPHA" in text

    assert any("cl /LD" in note for note in result.notes)
    assert any("QSpice" in note for note in result.notes)


def test_scaffold_spi_device_rejects_numeric_start(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(ValueError, match="device_name must start with a letter"):
        scaffold_spi_device("0_SPI_Dev", workspace_root=workspace, settings=None)


def test_scaffold_spi_device_custom_output_path(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = scaffold_spi_device(
        "ADC_Device",
        workspace_root=workspace,
        settings=None,
        output_path="spi/adc.cpp",
    )

    assert result.source_path.name == "adc.cpp"
    assert result.source_path.is_file()
    text = result.source_path.read_text(encoding="utf-8")
    assert "ADC_Device" in text


def test_scaffold_i2c_and_spi_outputs_are_different(tmp_path) -> None:
    """Ensure I2C and SPI scaffolds produce distinct templates."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    i2c = scaffold_i2c_device(
        "Dev", workspace_root=workspace, settings=None, output_path="i2c_dev.cpp"
    )
    spi = scaffold_spi_device(
        "Dev", workspace_root=workspace, settings=None, output_path="spi_dev.cpp"
    )

    i2c_text = i2c.source_path.read_text(encoding="utf-8")
    spi_text = spi.source_path.read_text(encoding="utf-8")

    assert "qspice_i2c" in i2c_text
    assert "qspice_spi" in spi_text
    assert "qspice_i2c" not in spi_text
    assert "qspice_spi" not in i2c_text
