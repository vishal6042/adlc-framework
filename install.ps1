# ADLC Framework installer (Windows / PowerShell)
# Registers this repo as a local plugin marketplace and installs the plugin,
# so /adlc and the ADLC agents/skills are available in every project.
#
# Usage:  ./install.ps1
# Re-runnable (idempotent).

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot

Write-Host "ADLC Framework — installing from: $repo" -ForegroundColor Cyan

$claude = (Get-Command claude -ErrorAction SilentlyContinue)
if (-not $claude) {
    Write-Warning "The 'claude' CLI was not found on PATH."
    Write-Host "Falling back to manual copy into ~/.claude/ ..."
    $dest = Join-Path $HOME ".claude"
    foreach ($d in @("agents", "skills", "commands")) {
        $src = Join-Path $repo $d
        if (Test-Path $src) {
            Copy-Item -Recurse -Force $src (Join-Path $dest $d)
            Write-Host "  copied $d -> ~/.claude/$d"
        }
    }
    Write-Host "Manual install complete. Restart Claude Code to pick up the components." -ForegroundColor Green
    return
}

# Preferred path: install as a plugin from this repo-as-marketplace.
& claude plugin marketplace add "$repo"
& claude plugin install "adlc-framework@adlc-framework-marketplace"

Write-Host ""
Write-Host "Installed. Next steps:" -ForegroundColor Green
Write-Host "  1. (optional) Copy .env.example to .env and add your Jira creds, or export JIRA_* vars."
Write-Host "  2. Open any project and run:  /adlc `"add a health endpoint`""
