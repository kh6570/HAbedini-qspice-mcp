# In the name of God, the Most Gracious, the Most Merciful
#Requires -Version 5.1

<#

.SYNOPSIS

  Quick MCP health check after setup_mcp.ps1

#>

[CmdletBinding()]

param(

    [int] $StartupBudgetSeconds = 30,

    [ValidateSet("Both", "ChatGPT")]
    [string] $Clients = "Both"

)



Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"



$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

$VerifyPy = Join-Path $RepoRoot "scripts\verify_mcp_stdio.py"

$CursorConfig = Join-Path $env:USERPROFILE ".cursor\mcp.json"

$VSCodeConfig = Join-Path $env:APPDATA "Code\User\mcp.json"



if (-not (Test-Path -LiteralPath $VenvPython)) {

    throw "Missing .venv. Run scripts/setup_mcp.ps1 first."

}

if ($Clients -eq "ChatGPT") {
    $CodexConfigRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
    $ChatGPTConfig = Join-Path $CodexConfigRoot "config.toml"
    & $VenvPython $VerifyPy $StartupBudgetSeconds --config $ChatGPTConfig
    if ($LASTEXITCODE -ne 0) { throw "ChatGPT desktop MCP verification failed" }
    Write-Host "ChatGPT desktop MCP server probe passed from Windows. Confirm /mcp in the app with the Windows native agent."
    return
}



$foundConfig = $false

foreach ($path in @($CursorConfig, $VSCodeConfig)) {

    if (-not (Test-Path -LiteralPath $path)) { continue }

    $raw = Get-Content -LiteralPath $path -Raw

    if ($raw -match '"qspice"') {

        $foundConfig = $true

        Write-Host "==> found qspice in $path"

    }

}

if (-not $foundConfig) {

    Write-Warning "No user-level qspice entry found. Run scripts/setup_mcp.ps1 first."

    Write-Warning "Expected Cursor: $CursorConfig"

    Write-Warning "Expected VS Code: $VSCodeConfig"

}



Write-Host "==> describe"

& $VenvPython -m qspice_mcp --describe --log-level error

if ($LASTEXITCODE -ne 0) { throw "--describe failed" }



Write-Host "==> tools/list probe (budget ${StartupBudgetSeconds}s)"

& $VenvPython $VerifyPy $StartupBudgetSeconds

if ($LASTEXITCODE -ne 0) {

    throw "MCP startup probe failed or exceeded ${StartupBudgetSeconds}s budget"

}



Write-Host "MCP verification passed."

