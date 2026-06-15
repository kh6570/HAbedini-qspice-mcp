#Requires -Version 5.1

<#

.SYNOPSIS

  First-time QSpice MCP setup for Cursor and VS Code (Windows).



.DESCRIPTION

  Creates/updates .venv, installs the package editable, detects QSPICE64.exe,

  merges qspice into user-level MCP config files, and runs --describe.



  Cursor: %USERPROFILE%\.cursor\mcp.json

  VS Code: %APPDATA%\Code\User\mcp.json



.EXAMPLE

  pwsh -ExecutionPolicy Bypass -File .\scripts\setup_mcp.ps1 -WorkspaceRoot "D:\circuits\buck"

#>

[CmdletBinding()]

param(

    [string] $WorkspaceRoot = "",

    [string] $QspiceExe = "",

    [ValidateSet("Cursor", "VSCode", "Both")]

    [string] $Clients = "Both",

    [switch] $SkipVenv,

    [switch] $SkipInstall

)



Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"



$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

$MergeScript = Join-Path $RepoRoot "scripts\merge_user_mcp_json.py"

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



function Install-Package {

    if ($SkipInstall) { return }

    Write-Step "Installing qspice-mcp editable in .venv"

    & $VenvPython -m pip install --upgrade pip | Out-Null

    & $VenvPython -m pip install -e $RepoRoot

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

    & $VenvPython $MergeScript $ConfigPath $RootKey "qspice" $tempEntry

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

if ($Clients -eq "Cursor" -or $Clients -eq "Both") {

    Write-Host "  Cursor config:      $CursorConfig"

}

if ($Clients -eq "VSCode" -or $Clients -eq "Both") {

    Write-Host "  VS Code config:     $VSCodeConfig"

}

Write-Host "  Next: Fully restart Cursor/VS Code, then check Settings -> Tools & MCP"

Write-Host "  Verify: pwsh -ExecutionPolicy Bypass -File .\scripts\verify_mcp.ps1"

