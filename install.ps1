# ADLC Framework installer (Windows / PowerShell)
#
#   ./install.ps1 <host> [target-project-dir]
#     host = claude | cline | gemini | universal | all
#     target-project-dir defaults to the current directory (for project-scoped hosts)
#
# Always regenerates adapters from core/ first (single source of truth).

param(
  [Parameter(Position=0)][ValidateSet("claude","cline","gemini","universal","all")][string]$HostName,
  [Parameter(Position=1)][string]$Target = $PWD
)

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot

function Pick-Python {
  foreach ($c in @("py","python3","python")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) { try { & $c -c "import sys" 2>$null; if ($LASTEXITCODE -eq 0) { return $c } } catch {} }
  }
  return $null
}

if (-not $HostName) { Write-Host "usage: ./install.ps1 <claude|cline|gemini|universal|all> [target-dir]"; exit 1 }
$py = Pick-Python
if (-not $py) { throw "No working python found (need py/python3)." }

Write-Host "Regenerating adapters from core/ ..." -ForegroundColor Cyan
Push-Location $repo; & $py build.py; Pop-Location

function Path-Hint {
  Write-Host ">> Add the ADLC scripts to PATH so 'adlc' resolves, e.g. (PowerShell profile):" -ForegroundColor Yellow
  Write-Host "     `$env:ADLC_HOME = '$repo\core'"
  Write-Host "     `$env:PATH = `"`$env:ADLC_HOME\scripts;`$env:PATH`""
}

function Install-Claude {
  $claude = Get-Command claude -ErrorAction SilentlyContinue
  if ($claude) {
    & claude plugin marketplace add "$repo\adapters\claude-code"
    & claude plugin install "adlc-framework@adlc-framework-marketplace"
    Write-Host "Claude Code plugin installed (scripts travel inside the plugin)." -ForegroundColor Green
  } else {
    Write-Host "'claude' CLI not found - manual copy into ~/.claude/ ..."
    $dest = Join-Path $HOME ".claude"
    foreach ($d in @("agents","skills","commands")) {
      Copy-Item -Recurse -Force "$repo\adapters\claude-code\$d" $dest -ErrorAction SilentlyContinue
    }
    Write-Host "Copied agents/skills/commands to ~/.claude/. Restart Claude Code."
    Path-Hint
  }
}

function Copy-Into-Project([string]$adapter, [string[]]$items) {
  foreach ($item in $items) {
    Copy-Item -Recurse -Force "$repo\adapters\$adapter\$item" $Target
    Write-Host "  copied $item -> $Target"
  }
}

switch ($HostName) {
  "claude"    { Install-Claude }
  "cline"     { Copy-Into-Project "cline" @(".clinerules"); Path-Hint }
  "gemini"    { Copy-Into-Project "gemini" @(".gemini","GEMINI.md"); Path-Hint }
  "universal" { Copy-Into-Project "universal" @("AGENTS.md"); Path-Hint }
  "all"       {
    Install-Claude
    Copy-Into-Project "cline" @(".clinerules")
    Copy-Into-Project "gemini" @(".gemini","GEMINI.md")
    Copy-Into-Project "universal" @("AGENTS.md")
    Path-Hint
  }
}

Write-Host ""
Write-Host "Done. Optional Jira: copy .env.example to .env (or set JIRA_* env vars)." -ForegroundColor Green
Write-Host 'Quick start: in your project, run the ADLC command/workflow with  "add a health endpoint"'
