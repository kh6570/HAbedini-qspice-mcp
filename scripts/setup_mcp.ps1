# In the name of God, the Most Gracious, the Most Merciful
#Requires -Version 5.1

<#

.SYNOPSIS

  First-time QSpice MCP setup for ChatGPT desktop, Cursor and VS Code (Windows).



.DESCRIPTION

  Creates/updates .venv, installs the package editable, detects QSPICE64.exe,

  merges qspice into user-level MCP config files, and runs --describe.



  Cursor: %USERPROFILE%\.cursor\mcp.json

  VS Code: %APPDATA%\Code\User\mcp.json

  ChatGPT desktop / Codex: %CODEX_HOME%\config.toml, or %USERPROFILE%\.codex\config.toml



.EXAMPLE

  pwsh -ExecutionPolicy Bypass -File .\scripts\setup_mcp.ps1 -WorkspaceRoot "D:\circuits\buck"

#>

[CmdletBinding()]

param(

    [string] $WorkspaceRoot = "",

    [string] $QspiceExe = "",

    [ValidateSet("ChatGPT", "Cursor", "VSCode", "Both")]

    [string] $Clients = "Both",

    [switch] $SkipVenv,

    [switch] $SkipInstall

)



Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"



$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

$MergeScript = Join-Path $RepoRoot "scripts\merge_user_mcp_json.py"

$MergeTomlScript = Join-Path $RepoRoot "scripts\merge_user_mcp_toml.py"

$CodexConfigRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }

$ChatGPTConfig = Join-Path $CodexConfigRoot "config.toml"

$CursorConfig = Join-Path $env:USERPROFILE ".cursor\mcp.json"

$VSCodeConfig = Join-Path $env:APPDATA "Code\User\mcp.json"

$DefaultWorkspace = Join-Path $env:USERPROFILE "Desktop\qspice-mcp-test"



function Write-Step([string] $Message) {

    Write-Host "==> $Message"

}



function Find-QspiceExe {

    if ($QspiceExe -and (Test-Path -LiteralPath $QspiceExe)) {

        return (Resolve-Path -LiteralPath $QspiceExe).Path

    }

    if ($env:QSPICE_EXE -and (Test-Path -LiteralPath $env:QSPICE_EXE)) {

        return (Resolve-Path -LiteralPath $env:QSPICE_EXE).Path

    }

    $candidates = @(

        "C:\Program Files\QSPICE\QSPICE64.exe",

        (Join-Path $env:LOCALAPPDATA "Programs\Qspice\QSPICE64.exe")

    )

    foreach ($candidate in $candidates) {

        if (Test-Path -LiteralPath $candidate) {

            return (Resolve-Path -LiteralPath $candidate).Path

        }

    }

    return $null

}



function Ensure-Venv {

    if ($SkipVenv) { return }

    if (Test-Path -LiteralPath $VenvPython) {

        Write-Step "Virtualenv already exists: $VenvPython"

        return

    }

    Write-Step "Creating virtualenv in $RepoRoot\.venv"

    & python -m venv (Join-Path $RepoRoot ".venv")

    if (-not (Test-Path -LiteralPath $VenvPython)) {

        throw "Failed to create virtualenv. Is Python 3.11+ installed and on PATH?"

    }

}



function Find-LocalCore {

    if ($env:MCP_CORE_PATH -and (Test-Path (Join-Path $env:MCP_CORE_PATH "src\mcp_app_core\__init__.py"))) {

        return $env:MCP_CORE_PATH

    }

    $parent = Split-Path -Parent $RepoRoot

    $found = @()

    foreach ($dir in Get-ChildItem -Path $parent -Directory -ErrorAction SilentlyContinue) {

        $marker = Join-Path $dir.FullName "src\mcp_app_core\__init__.py"

        if ((Test-Path -LiteralPath $marker) -and ($dir.FullName -ne $RepoRoot)) {

            $found += $dir.FullName

        }

    }

    if ($found.Count -eq 1) { return $found[0] }

    return $null

}



function Install-Package {

    if ($SkipInstall) { return }

    Write-Step "Installing qspice-mcp editable in .venv"

    & $VenvPython -m pip install --upgrade pip | Out-Null

    $core = Find-LocalCore

    if ($core) {

        $env:MCP_CORE_PATH = $core

        Write-Step "Using local mcp-app-core checkout"

    }

    $InstallTarget = if ($Clients -eq "ChatGPT") { "${RepoRoot}[setup]" } else { $RepoRoot }

    & $VenvPython -m pip install -e $InstallTarget

    if ($LASTEXITCODE -ne 0) { throw "Failed to install qspice-mcp" }

    if ($core) {

        & $VenvPython -m pip install -e $core --no-deps

    }

}



function Resolve-WorkspaceRoot {

    if ($WorkspaceRoot) {

        $resolved = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($WorkspaceRoot)

        if (-not (Test-Path -LiteralPath $resolved)) {

            New-Item -ItemType Directory -Path $resolved -Force | Out-Null

            Write-Step "Created simulation workspace: $resolved"

        }

        return (Resolve-Path -LiteralPath $resolved).Path

    }

    if (-not (Test-Path -LiteralPath $DefaultWorkspace)) {

        New-Item -ItemType Directory -Path $DefaultWorkspace -Force | Out-Null

        Write-Step "Created default simulation workspace: $DefaultWorkspace"

    }

    return (Resolve-Path -LiteralPath $DefaultWorkspace).Path

}



function Write-QspiceServerEntry([string] $SimWorkspace, [string] $QspicePath) {

    @{

        type    = "stdio"

        command = $VenvPython

        args    = @(

            "-u", "-m", "qspice_mcp",

            "--workspace-root", $SimWorkspace,

            "--log-level", "error"

        )

        env     = @{

            QSPICE_EXE        = $QspicePath

            QSPICE_LOG_LEVEL  = "error"

            QSPICE_DEV_WATCH  = "0"

        }

    }

}



function Merge-UserMcpConfig(

    [string] $ConfigPath,

    [string] $RootKey,

    [string] $SimWorkspace,

    [string] $QspicePath

) {

    $entry = Write-QspiceServerEntry -SimWorkspace $SimWorkspace -QspicePath $QspicePath

    $tempEntry = Join-Path $env:TEMP "qspice-mcp-server-entry.json"

    $entry | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $tempEntry -Encoding utf8

    if ($RootKey -eq "mcp_servers") {
        & $VenvPython $MergeTomlScript $ConfigPath "qspice" $tempEntry
    } else {
        & $VenvPython $MergeScript $ConfigPath $RootKey "qspice" $tempEntry
    }

    if ($LASTEXITCODE -ne 0) {

        throw "Failed to merge user MCP config at $ConfigPath"

    }

    Write-Step "Updated user MCP config: $ConfigPath"

}



function Test-Describe([string] $QspicePath, [string] $SimWorkspace) {

    Write-Step "Running qspice_mcp --describe"

    $env:QSPICE_EXE = $QspicePath

    & $VenvPython -m qspice_mcp --describe --workspace-root $SimWorkspace --log-level error

    if ($LASTEXITCODE -ne 0) {

        throw "qspice_mcp --describe failed with exit code $LASTEXITCODE"

    }

}



Write-Step "Repo root: $RepoRoot"

Ensure-Venv

Install-Package



$resolvedQspice = Find-QspiceExe

if (-not $resolvedQspice) {

    throw @"

QSPICE64.exe not found. Install QSpice or pass -QspiceExe 'C:\Program Files\QSPICE\QSPICE64.exe'

"@

}

Write-Step "QSpice executable: $resolvedQspice"



$simWorkspace = Resolve-WorkspaceRoot

Write-Step "Simulation workspace: $simWorkspace"



if ($Clients -eq "ChatGPT") {
    Merge-UserMcpConfig -ConfigPath $ChatGPTConfig -RootKey "mcp_servers" -SimWorkspace $simWorkspace -QspicePath $resolvedQspice
}

if ($Clients -eq "Cursor" -or $Clients -eq "Both") {

    Merge-UserMcpConfig -ConfigPath $CursorConfig -RootKey "mcpServers" -SimWorkspace $simWorkspace -QspicePath $resolvedQspice

}

if ($Clients -eq "VSCode" -or $Clients -eq "Both") {

    Merge-UserMcpConfig -ConfigPath $VSCodeConfig -RootKey "servers" -SimWorkspace $simWorkspace -QspicePath $resolvedQspice

}





Test-Describe -QspicePath $resolvedQspice -SimWorkspace $simWorkspace



Write-Host ""

Write-Host "Setup complete."

Write-Host "  Repo / venv:        $RepoRoot"

Write-Host "  Simulation workspace: $simWorkspace"

if ($Clients -eq "ChatGPT") {
    Write-Host "  ChatGPT desktop:    $ChatGPTConfig"
    Write-Host "  Agent environment:  Windows native (Settings -> Agent environment; restart after changing)"
    Write-Host "  Next: Restart ChatGPT desktop; Settings -> MCP servers; use /mcp to check qspice"
}

if ($Clients -eq "Cursor" -or $Clients -eq "Both") {

    Write-Host "  Cursor config:      $CursorConfig"

}

if ($Clients -eq "VSCode" -or $Clients -eq "Both") {

    Write-Host "  VS Code config:     $VSCodeConfig"

}

if ($Clients -ne "ChatGPT") {
    Write-Host "  Next: Fully restart Cursor/VS Code, then check their MCP settings"
}

if ($Clients -eq "ChatGPT") {
    Write-Host "  Verify: pwsh -ExecutionPolicy Bypass -File .\scripts\verify_mcp.ps1 -Clients ChatGPT"
} else {
    Write-Host "  Verify: pwsh -ExecutionPolicy Bypass -File .\scripts\verify_mcp.ps1"
}

