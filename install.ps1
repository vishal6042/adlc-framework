# ADLC Framework installer (Windows / PowerShell). Thin wrapper around install.py.
#
#   ./install.ps1 <claude|cline|gemini|universal|all> [target-dir] [--uninstall] [--dry-run] [--no-path]
#
# The framework stays in this folder. Nothing is published to a marketplace.
# Keep this file ASCII-only (Windows PowerShell 5.1 reads BOM-less files as ANSI).

$ErrorActionPreference = 'Stop'
$installer = Join-Path $PSScriptRoot 'install.py'

foreach ($c in @('py', 'python3', 'python')) {
  if (-not (Get-Command $c -ErrorAction SilentlyContinue)) { continue }
  $ErrorActionPreference = 'Continue'
  & $c -c 'import sys; assert sys.version_info >= (3, 8)' 2>$null | Out-Null
  $ok = ($LASTEXITCODE -eq 0)
  $ErrorActionPreference = 'Stop'
  if ($ok) {
    & $c $installer @args
    exit $LASTEXITCODE
  }
}
Write-Error 'ADLC needs Python 3.8+ (tried py, python3, python). Install it from python.org and re-run.'
exit 1
