<#
.SYNOPSIS
    Quality gate: ruff → format-check → mypy → pytest → coverage floors.
    Only prints failures by default. Use -Verbose to see all output.
#>
param([switch]$Verbose)

$ErrorActionPreference = "Stop"
$venvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"

function Invoke-Check {
    param(
        [string]$Label,
        [scriptblock]$Command,
        [switch]$AlwaysQuiet
    )
    if ($Verbose -or $AlwaysQuiet) {
        & $Command
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        return
    }
    $output = & $Command 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n=== FAILED: $Label ===" -ForegroundColor Red
        Write-Output $output
        exit $LASTEXITCODE
    }
    Write-Host "[OK] $Label" -ForegroundColor Green
}

Invoke-Check -Label "ruff" -AlwaysQuiet {
    & $venvPython -m ruff check .
}

Invoke-Check -Label "ruff format" -AlwaysQuiet {
    & $venvPython -m ruff format --check .
}

Invoke-Check -Label "mypy" -AlwaysQuiet {
    & $venvPython -m mypy --strict src/
}

Invoke-Check -Label "pytest" {
    & $venvPython -m pytest -m "not integration" --cov -q --tb=short --no-header
}

Invoke-Check -Label "coverage floors" {
    & $venvPython (Join-Path $PSScriptRoot "check_package_coverage.py")
}

Write-Host "`nAll quality gates passed." -ForegroundColor Green
