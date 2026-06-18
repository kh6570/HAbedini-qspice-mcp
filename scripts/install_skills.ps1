#Requires -Version 5.1

<#
.SYNOPSIS
  Install bundled QSpice agent skills into your AI agent's skills directory.

.DESCRIPTION
  Copies (or symlinks) the QSpice skills catalog shipped inside the qspice-mcp
  package into a skills directory your agent discovers. The catalog itself is
  tracked, public package data; this script only writes machine-local copies.

  Locates the catalog from the installed package first
  (importlib.resources qspice_mcp.data.skills), then falls back to the repo's
  src/qspice_mcp/data/skills when run from a checkout.

.PARAMETER SkillsRoot
  Target skills directory. Defaults to ~/.agents/skills (discovered by most
  MCP-aware agents). For Claude Code plugins or other layouts, point this at the
  directory your agent reads.

.PARAMETER Groups
  Skill groups to install. Defaults to qspice-core.

.PARAMETER Symlink
  Create directory symlinks instead of copying (requires privilege on Windows).

.PARAMETER Force
  Overwrite existing skills of the same name.

.EXAMPLE
  pwsh -File scripts/install_skills.ps1

.EXAMPLE
  pwsh -File scripts/install_skills.ps1 -SkillsRoot "$HOME/.agents/skills" -Force
#>

[CmdletBinding()]
param(
    [string]   $SkillsRoot = (Join-Path $HOME ".agents/skills"),
    [string[]] $Groups = @("qspice-core"),
    [switch]   $Symlink,
    [switch]   $Force
)

$ErrorActionPreference = "Stop"

function Resolve-CatalogRoot {
    # 1) Installed package via importlib.resources
    foreach ($py in @("python", "python3", "py")) {
        try {
            $out = & $py -c "import importlib.resources as r; print(r.files('qspice_mcp.data.skills'))" 2>$null
            if ($LASTEXITCODE -eq 0 -and $out) {
                $path = $out.Trim()
                if (Test-Path $path) { return $path }
            }
        }
        catch { continue }
    }
    # 2) Repo checkout fallback (script lives in <repo>/scripts)
    $repoCatalog = Join-Path $PSScriptRoot "..\src\qspice_mcp\data\skills"
    if (Test-Path $repoCatalog) { return (Resolve-Path $repoCatalog).Path }
    throw "Could not locate the QSpice skills catalog (qspice_mcp.data.skills)."
}

$catalogRoot = Resolve-CatalogRoot
Write-Host "Skills catalog: $catalogRoot"

if (-not (Test-Path $SkillsRoot)) {
    New-Item -ItemType Directory -Path $SkillsRoot -Force | Out-Null
}
Write-Host "Skills target:  $SkillsRoot"

$installed = 0
foreach ($group in $Groups) {
    $groupDir = Join-Path $catalogRoot $group
    if (-not (Test-Path $groupDir)) {
        Write-Warning "Group not found, skipping: $group"
        continue
    }

    $skillDirs = Get-ChildItem -Path $groupDir -Directory -ErrorAction SilentlyContinue
    foreach ($skill in $skillDirs) {
        if (-not (Test-Path (Join-Path $skill.FullName "SKILL.md"))) { continue }
        $dest = Join-Path $SkillsRoot $skill.Name

        if (Test-Path $dest) {
            if (-not $Force) {
                Write-Warning "Exists (use -Force to overwrite): $($skill.Name)"
                continue
            }
            Remove-Item -Recurse -Force $dest
        }

        if ($Symlink) {
            New-Item -ItemType SymbolicLink -Path $dest -Target $skill.FullName | Out-Null
            Write-Host "Linked  $($skill.Name)"
        }
        else {
            Copy-Item -Recurse -Path $skill.FullName -Destination $dest
            Write-Host "Copied  $($skill.Name)"
        }
        $installed++
    }
}

Write-Host ""
Write-Host "Installed $installed skill(s) into $SkillsRoot"
Write-Host "Restart your agent (or reload skills) to pick them up."
