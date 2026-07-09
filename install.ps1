# ADLC Framework installer (Windows / PowerShell) — LOCAL, NO MARKETPLACE.
#
#   ./install.ps1 <host> [target-project-dir]
#     host = claude | cline | gemini | universal | all
#
# Model: the framework stays put in THIS folder (the common place). We add its
# scripts to your PATH once, then drop each host's small instruction files into
# that host's USER-GLOBAL config dir, so every project can use it. Nothing is
# published to a marketplace or plugin registry — not even for Claude Code.

param(
  [Parameter(Position=0)][ValidateSet("claude","cline","gemini","universal","all")][string]$HostName,
  [Parameter(Position=1)][string]$Target = $PWD
)

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$scriptsDir = Join-Path $repo "core\scripts"

function Pick-Python {
  foreach ($c in @("py","python3","python")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) { try { & $c -c "import sys" 2>$null; if ($LASTEXITCODE -eq 0) { return $c } } catch {} }
  }
  return $null
}

function Add-ToUserPath([string]$dir) {
  $cur = [Environment]::GetEnvironmentVariable("Path", "User")
  if (($cur -split ';') -notcontains $dir) {
    [Environment]::SetEnvironmentVariable("Path", "$cur;$dir", "User")
    Write-Host "  added to your user PATH: $dir  (open a new terminal to pick it up)"
  } else {
    Write-Host "  already on PATH: $dir"
  }
  $env:PATH = "$dir;$env:PATH"   # current session too
}

if (-not $HostName) { Write-Host "usage: ./install.ps1 <claude|cline|gemini|universal|all> [target-dir]"; exit 1 }
$py = Pick-Python
if (-not $py) { throw "No working python found (need py/python3)." }

Write-Host "1) Regenerating adapters from core/ ..." -ForegroundColor Cyan
Push-Location $repo; & $py build.py; Pop-Location

Write-Host "2) Registering the shared framework (common place = $repo)" -ForegroundColor Cyan
[Environment]::SetEnvironmentVariable("ADLC_HOME", (Join-Path $repo "core"), "User")
$env:ADLC_HOME = (Join-Path $repo "core")
Add-ToUserPath $scriptsDir

function Ensure-Dir([string]$p) { New-Item -ItemType Directory -Force $p | Out-Null; $p }

function Install-Claude {
  # User-global Claude Code config — applies to ALL projects, no plugin/marketplace.
  $base = Ensure-Dir (Join-Path $HOME ".claude")
  foreach ($d in @("agents","skills","commands")) {
    Copy-Item -Recurse -Force (Join-Path $repo "adapters\claude-code\$d\*") (Ensure-Dir (Join-Path $base $d))
  }
  Write-Host "  Claude: copied agents/skills/commands into ~/.claude/  (/adlc available in every project)"
}

function Install-Cline {
  # Cline global rules + workflows — apply across all projects.
  $rules = Ensure-Dir (Join-Path $HOME "Documents\Cline\Rules")
  $flows = Ensure-Dir (Join-Path $HOME "Documents\Cline\Workflows")
  Copy-Item -Force (Join-Path $repo "adapters\cline\.clinerules\adlc.md") $rules
  Copy-Item -Force (Join-Path $repo "adapters\cline\.clinerules\workflows\adlc.md") (Join-Path $flows "adlc.md")
  Write-Host "  Cline: installed global rule + workflow under ~/Documents/Cline/"
}

function Install-Gemini {
  $cmds = Ensure-Dir (Join-Path $HOME ".gemini\commands")
  Copy-Item -Force (Join-Path $repo "adapters\gemini\.gemini\commands\adlc.toml") $cmds
  Copy-Item -Force (Join-Path $repo "adapters\gemini\GEMINI.md") (Ensure-Dir (Join-Path $HOME ".gemini"))
  Write-Host "  Gemini: installed user command ~/.gemini/commands/adlc.toml"
}

function Install-Universal {
  # AGENTS.md is per-repo by nature; drop it into the target project.
  Copy-Item -Force (Join-Path $repo "adapters\universal\AGENTS.md") $Target
  Write-Host "  Universal: copied AGENTS.md into $Target"
}

Write-Host "3) Installing host instruction files (no marketplace)" -ForegroundColor Cyan
switch ($HostName) {
  "claude"    { Install-Claude }
  "cline"     { Install-Cline }
  "gemini"    { Install-Gemini }
  "universal" { Install-Universal }
  "all"       { Install-Claude; Install-Cline; Install-Gemini; Install-Universal }
}

Write-Host ""
Write-Host "Done. Restart your editor/terminal so PATH + ADLC_HOME take effect." -ForegroundColor Green
Write-Host "Optional Jira: copy .env.example to .env or set JIRA_* env vars."
Write-Host 'Then in ANY project run the ADLC command with:  "add a health endpoint"'
