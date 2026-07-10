# adlc.ps1 — PowerShell parity for Windows hosts without Git Bash.
# Mirrors the common subcommands of the bash `adlc`. Deterministic, no LLM.
#
#   .\adlc.ps1 next-key
#   .\adlc.ps1 constitution
#   .\adlc.ps1 clarifications <KEY>
#   .\adlc.ps1 detect-stack
#   .\adlc.ps1 min-coverage
#   .\adlc.ps1 init "<request>" [KEY]
#   .\adlc.ps1 status <KEY>
#   .\adlc.ps1 get-state <KEY> <field>
#   .\adlc.ps1 set-state <KEY> <field> <value>
#   .\adlc.ps1 approve <KEY> gate1|gate2
#   .\adlc.ps1 compare-url <branch>

param([Parameter(Position=0)][string]$Cmd = "help",
      [Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Templates = Join-Path $ScriptDir "..\templates"

function StateFile($key) { "docs/adlc/$key/state.md" }

function Next-Key {
  $d = "docs/adlc/tickets"; $max = 0
  if (Test-Path $d) {
    Get-ChildItem "$d/ADLC-*.md" -ErrorAction SilentlyContinue | ForEach-Object {
      if ($_.BaseName -match '^ADLC-(\d+)$') { $n = [int]$Matches[1]; if ($n -gt $max) { $max = $n } }
    }
  }
  "ADLC-{0:D3}" -f ($max + 1)
}

function Get-State($key, $field) {
  $sf = StateFile $key
  if (-not (Test-Path $sf)) { return "" }
  foreach ($line in Get-Content $sf) {
    if ($line -match "^- $field:\s*(.*)$") { return $Matches[1] }
  }
  ""
}

function Set-State($key, $field, $value) {
  $sf = StateFile $key
  if (-not (Test-Path $sf)) { throw "no state file for $key (run: adlc init)" }
  $lines = Get-Content $sf
  if ($lines -match "^- $field:") {
    $lines = $lines -replace "^- $field:.*", "- $field: $value"
  } else {
    $lines += "- $field: $value"
  }
  Set-Content -Path $sf -Value $lines -Encoding utf8
}

function Compare-Url($branch) {
  $remote = (git remote get-url origin 2>$null)
  if (-not $remote) { return "" }
  $url = $remote -replace '\.git$', ''
  if ($url -match '^git@([^:]+):(.*)$') { $url = "https://$($Matches[1])/$($Matches[2])" }
  elseif ($url -match '^ssh://git@(.*)$') { $url = "https://$($Matches[1])" }
  "$url/compare/$branch`?expand=1"
}

switch ($Cmd) {
  "next-key"    { Next-Key }
  "constitution" {
    $cfile = "docs/adlc/constitution.md"
    if (-not (Test-Path $cfile)) {
      New-Item -ItemType Directory -Force "docs/adlc" | Out-Null
      $today = (Get-Date -Format "yyyy-MM-dd")
      (Get-Content (Join-Path $Templates "constitution.md") -Raw).Replace("<DATE>", $today) |
        Set-Content $cfile -Encoding utf8
      Write-Error "created $cfile — edit it to set your project's principles"
    }
    $cfile
  }
  "clarifications" {
    $key = $Rest[0]; $found = $false
    foreach ($f in @("docs/adlc/$key/ticket.md", "docs/adlc/$key/spec.md", "docs/adlc/$key/tasks.md")) {
      if (-not (Test-Path $f)) { continue }
      Select-String -Path $f -Pattern '\[NEEDS CLARIFICATION:' | ForEach-Object {
        $found = $true; "{0}:{1}:{2}" -f $f, $_.LineNumber, $_.Line.Trim()
      }
    }
    if ($found) { exit 1 } else { "no open clarifications for $key" }
  }
  "detect-stack" {
    $f = @()
    if (Test-Path pom.xml) { $f += "java-maven" }
    if ((Test-Path build.gradle) -or (Test-Path build.gradle.kts)) {
      $android = $false
      Get-ChildItem -Recurse -Depth 4 -Filter AndroidManifest.xml -ErrorAction SilentlyContinue | ForEach-Object { $android = $true }
      if ($android) { $f += "android" } else { $f += "java-gradle" }
    }
    if (Test-Path package.json) {
      $pkg = Get-Content package.json -Raw
      if ($pkg -match '"react"') { $f += "react" }
      elseif ($pkg -match '"vue"') { $f += "vue" }
      elseif ($pkg -match '"@angular/core"') { $f += "angular" }
      else { $f += "node" }
    }
    if ((Test-Path pyproject.toml) -or (Test-Path setup.py) -or (Test-Path requirements.txt)) { $f += "python" }
    if (Test-Path go.mod) { $f += "go" }
    if (Test-Path Cargo.toml) { $f += "rust" }
    if (Test-Path Gemfile) { $f += "ruby" }
    if (Test-Path composer.json) { $f += "php" }
    if ((Get-ChildItem *.csproj, *.sln -ErrorAction SilentlyContinue)) { $f += "dotnet" }
    if ($f.Count) { $f -join " " } else { "unknown" }
  }
  "min-coverage" { if ($env:ADLC_MIN_COVERAGE) { $env:ADLC_MIN_COVERAGE } else { "90" } }
  "status"      { Get-Content (StateFile $Rest[0]) }
  "get-state"   { Get-State $Rest[0] $Rest[1] }
  "set-state"   { Set-State $Rest[0] $Rest[1] $Rest[2]; "ok" }
  "compare-url" { Compare-Url $Rest[0] }
  "approve" {
    $key = $Rest[0]; $gate = $Rest[1]
    if ($gate -eq "gate1") { Set-State $key "gate1_spec_approved" "true" }
    elseif ($gate -eq "gate2") { Set-State $key "gate2_push_approved" "true" }
    else { throw "gate must be gate1 or gate2" }
    "recorded $gate approval for $key"
  }
  "init" {
    $req = $Rest[0]; $key = if ($Rest.Count -ge 2) { $Rest[1] } else { Next-Key }
    $today = (Get-Date -Format "yyyy-MM-dd")
    $slug = ($req.ToLower() -replace '[^a-z0-9]+','-').Trim('-')
    $branch = "$(if ($env:ADLC_BRANCH_PREFIX) { $env:ADLC_BRANCH_PREFIX } else { 'adlc' })/$key-$slug"
    New-Item -ItemType Directory -Force "docs/adlc/$key" | Out-Null
    New-Item -ItemType Directory -Force "docs/adlc/tickets" | Out-Null
    (Get-Content (Join-Path $Templates "state.md") -Raw).
      Replace("<KEY>", $key).Replace("<TITLE>", $req).Replace("<DATE>", $today).Replace("<BRANCH>", $branch) |
      Set-Content (StateFile $key) -Encoding utf8
    $ticket = (Get-Content (Join-Path $Templates "ticket.md") -Raw).
      Replace("<KEY>", $key).Replace("<TITLE>", $req).Replace("<DATE>", $today)
    $ticket | Set-Content "docs/adlc/$key/ticket.md" -Encoding utf8
    $ticket | Set-Content "docs/adlc/tickets/$key.md" -Encoding utf8
    $key
  }
  default {
    "adlc.ps1 — deterministic ADLC ops. Subcommands: next-key, constitution, clarifications, detect-stack, min-coverage, init, status, get-state, set-state, approve, compare-url."
  }
}
