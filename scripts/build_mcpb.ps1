#Requires -Version 5.1
<#
.SYNOPSIS
  Build a .mcpb install bundle for the QSpice MCP server.

.DESCRIPTION
  Packs the repo-root manifest.json plus the source tree into a single-click
  `.mcpb` bundle (a zip archive). Uses the official `mcpb` CLI when available
  (npx @anthropic-ai/mcpb), otherwise falls back to a self-contained staged
  Compress-Archive so the bundle always builds.

  The manifest uses the `uv` server type, so dependencies are resolved by the
  host from pyproject.toml at install time -- no venv/server lib is bundled.

.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File .\scripts\build_mcpb.ps1

.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File .\scripts\build_mcpb.ps1 -ForceZip
#>
[CmdletBinding()]
param(
    [string] $OutputDir = "dist",
    [string] $BundleName = "qspice-mcp.mcpb",
    [switch] $ForceZip
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ManifestPath = Join-Path $RepoRoot "manifest.json"
$OutputRoot = if ([System.IO.Path]::IsPathRooted($OutputDir)) { $OutputDir } else { Join-Path $RepoRoot $OutputDir }
$BundlePath = Join-Path $OutputRoot $BundleName

function Write-Step([string] $Message) { Write-Host "==> $Message" }

function Test-Manifest {
    if (-not (Test-Path -LiteralPath $ManifestPath)) {
        throw "manifest.json not found at $ManifestPath"
    }
    try {
        $manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
    }
    catch {
        throw "manifest.json is not valid JSON: $($_.Exception.Message)"
    }
    foreach ($field in @("manifest_version", "name", "version", "server")) {
        if (-not $manifest.PSObject.Properties.Name.Contains($field)) {
            throw "manifest.json is missing required field '$field'"
        }
    }
    Write-Step "Manifest OK: $($manifest.name) v$($manifest.version) (manifest_version $($manifest.manifest_version))"
}

function Build-WithCli {
    $npx = Get-Command npx -ErrorAction SilentlyContinue
    if (-not $npx) { return $false }
    Write-Step "Packing with official mcpb CLI (npx @anthropic-ai/mcpb)"
    & npx --yes @anthropic-ai/mcpb pack $RepoRoot $BundlePath
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "mcpb CLI pack failed (exit $LASTEXITCODE); falling back to staged zip."
        return $false
    }
    return $true
}

function Build-WithZip {
    Write-Step "Packing with staged Compress-Archive fallback"
    $staging = Join-Path ([System.IO.Path]::GetTempPath()) ("qspice-mcpb-" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $staging -Force | Out-Null
    try {
        Copy-Item -LiteralPath $ManifestPath -Destination (Join-Path $staging "manifest.json")
        foreach ($file in @("pyproject.toml", "README.md", "LICENSE", "CHANGELOG.md")) {
            $src = Join-Path $RepoRoot $file
            if (Test-Path -LiteralPath $src) {
                Copy-Item -LiteralPath $src -Destination (Join-Path $staging $file)
            }
        }
        $srcDir = Join-Path $RepoRoot "src"
        $destSrc = Join-Path $staging "src"
        Copy-Item -LiteralPath $srcDir -Destination $destSrc -Recurse
        Get-ChildItem -LiteralPath $destSrc -Recurse -Directory -Filter "__pycache__" |
            Remove-Item -Recurse -Force
        Get-ChildItem -LiteralPath $destSrc -Recurse -File -Include "*.pyc" |
            Remove-Item -Force

        $zipPath = [System.IO.Path]::ChangeExtension($BundlePath, ".zip")
        if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
        Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipPath -Force
        if (Test-Path -LiteralPath $BundlePath) { Remove-Item -LiteralPath $BundlePath -Force }
        Rename-Item -LiteralPath $zipPath -NewName $BundleName
    }
    finally {
        Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Step "Repo root: $RepoRoot"
Test-Manifest

if (-not (Test-Path -LiteralPath $OutputRoot)) {
    New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
}

$packed = $false
if (-not $ForceZip) {
    $packed = Build-WithCli
}
if (-not $packed) {
    Build-WithZip
}

if (-not (Test-Path -LiteralPath $BundlePath)) {
    throw "Bundle was not produced at $BundlePath"
}

$sizeKb = [math]::Round((Get-Item -LiteralPath $BundlePath).Length / 1KB, 1)
Write-Host ""
Write-Host "Bundle built: $BundlePath ($sizeKb KB)"
Write-Host "  Install: drag the .mcpb into Claude Desktop (Settings -> Extensions),"
Write-Host "           or any MCPB-aware client, then set QSPICE64.exe + workspace."
