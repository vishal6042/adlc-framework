# adlc.ps1 - PowerShell twin of the bash `adlc` (same commands, output and exit codes).
# Deterministic, no LLM. Works on Windows PowerShell 5.1 and PowerShell 7+.
#
# KEEP THIS FILE ASCII-ONLY: Windows PowerShell 5.1 reads BOM-less files as ANSI,
# so a single non-ASCII character (e.g. an em dash) can break parsing.
#
# No param() block on purpose: arguments such as --no-push must reach $args as-is.
# Exit codes: 0 ok, 1 error, 2 bad usage, 3 push failed (commit kept locally).

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$ScriptDir = $PSScriptRoot
$Templates = Join-Path $ScriptDir '../templates'   # forward slashes work on every OS
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$KeyRe = '^[A-Za-z][A-Za-z0-9_]*-[0-9]+$'
$FieldRe = '^[a-z][a-z0-9_]*$'
$SecretRe = '(^|/)(\.env(\.[^/]*)?|[^/]*\.(pem|key|p12|pfx|keystore|jks|token)|id_(rsa|dsa|ecdsa|ed25519)[^/]*|\.npmrc|\.pypirc|\.netrc|credentials(\.json)?|secrets?\.(json|ya?ml|toml))$'
$SecretOkRe = '\.(example|sample|template|dist)$'
$script:NativeCode = 0

function Fail([string]$msg, [int]$code = 1) {
  [Console]::Error.WriteLine("adlc: $msg")
  exit $code
}
function UsageError([string]$msg) {
  [Console]::Error.WriteLine("adlc: $msg")
  [Console]::Error.WriteLine("run 'adlc help' for usage")
  exit 2
}

function Show-Usage {
@'
adlc - deterministic ADLC operations

Usage:
  adlc init "<request>" [KEY]       create docs/adlc/<KEY>/ with state.md + ticket.md
  adlc next-key                     print the next local ticket key (ADLC-00N)
  adlc status <KEY>                 print the run's state file
  adlc get-state <KEY> <field>      read one state field
  adlc set-state <KEY> <f> <value>  write one state field
  adlc approve <KEY> gate1|gate2    record a human approval
  adlc scaffold <KEY> spec|tasks|verification [--force]
                                    write a template into docs/adlc/<KEY>/
  adlc constitution                 create (if missing) and print docs/adlc/constitution.md
  adlc clarifications <KEY>         list open [NEEDS CLARIFICATION: ...] markers (exit 1 if any)
  adlc detect-stack                 print the project's detected stack(s)
  adlc min-coverage                 print the coverage floor (ADLC_MIN_COVERAGE or 90)
  adlc branch <KEY>                 check out (create if needed) the feature branch
  adlc compare-url <branch>         print the PR/MR URL for the origin remote
  adlc ship <KEY> [--no-push]       commit (+push) the change, print the PR URL
  adlc jira mode|pick|create ...    Jira Cloud helper (needs Python 3.8+)
  adlc doctor                       check that git, python and config are usable
  adlc version                      print the framework version

Environment: ADLC_BRANCH_PREFIX (default adlc), ADLC_REMOTE (default origin),
ADLC_DOCS_DIR (default <repo>/docs/adlc), ADLC_MIN_COVERAGE (default 90),
JIRA_* (see .env.example).
'@
}

# --- native commands ---------------------------------------------------------
# Windows PowerShell (and pwsh < 7.3) drop embedded double quotes when passing
# arguments to native programs; escape them the way the C runtime expects.
function Convert-NativeArg([string]$a) {
  # Compare numbers: PSVersion is [version] on 5.1 but [semver] on 7+.
  $v = $PSVersionTable.PSVersion
  $legacy = ($v.Major -lt 7) -or ($v.Major -eq 7 -and $v.Minor -lt 3)
  if (-not $legacy) {
    $mode = Get-Variable PSNativeCommandArgumentPassing -ValueOnly -ErrorAction SilentlyContinue
    $legacy = ($mode -eq 'Legacy')
  }
  if (-not $legacy -or $a -notmatch '"') { return $a }
  $a = [regex]::Replace($a, '(\\*)"', [System.Text.RegularExpressions.MatchEvaluator]{
      param($m) ($m.Groups[1].Value * 2) + '\"' })
  if ($a -match '\s' -and $a -match '(\\+)$') { $a = $a + $Matches[1] }
  return $a
}

# Run a native program. -Quiet hides stderr. Exit code lands in $script:NativeCode.
function Invoke-Native([string]$exe, [string[]]$argv = @(), [switch]$Quiet) {
  $fixed = @($argv | ForEach-Object { Convert-NativeArg $_ })
  $old = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    if ($Quiet) { $out = & $exe @fixed 2>$null } else { $out = & $exe @fixed }
    $script:NativeCode = $LASTEXITCODE
  } finally { $ErrorActionPreference = $old }
  return $out
}
function Invoke-Git([string[]]$argv, [switch]$Quiet) {
  $out = Invoke-Native 'git' $argv -Quiet:$Quiet
  if ($null -eq $out) { return '' }
  return (@($out) -join "`n").Trim()
}

# Quote one argument for a Windows command line (MSVCRT rules).
function ConvertTo-CmdArg([string]$a) {
  if ($a -eq '') { return '""' }
  if ($a -notmatch '[\s"]') { return $a }
  $a = [regex]::Replace($a, '(\\*)"', [System.Text.RegularExpressions.MatchEvaluator]{
      param($m) ($m.Groups[1].Value * 2) + '\"' })
  $a = [regex]::Replace($a, '(\\+)$', [System.Text.RegularExpressions.MatchEvaluator]{
      param($m) $m.Groups[1].Value * 2 })
  return '"' + $a + '"'
}

# Run a program with its stdout/stderr going straight to ours. Unlike `& exe`,
# PowerShell 5.1 does not wrap the child's stderr in error records. Returns the exit code.
function Invoke-Passthrough([string]$exe, [string[]]$argv = @()) {
  $cmd = Get-Command $exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $cmd) { Fail "$exe not found on PATH" }
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $cmd.Path
  $psi.Arguments = (@($argv | ForEach-Object { ConvertTo-CmdArg $_ }) -join ' ')
  $psi.UseShellExecute = $false
  $psi.WorkingDirectory = Get-Here
  $p = [System.Diagnostics.Process]::Start($psi)
  $p.WaitForExit()
  return $p.ExitCode
}

# --- locations ---------------------------------------------------------------
function Get-Here { (Get-Location).ProviderPath }
function Resolve-Abs([string]$p) {
  if ([IO.Path]::IsPathRooted($p)) { return $p }
  return (Join-Path (Get-Here) $p)
}
function Get-ProjectRoot {
  if (Get-Command git -ErrorAction SilentlyContinue) {
    $r = Invoke-Git @('rev-parse', '--show-toplevel') -Quiet
    if ($script:NativeCode -eq 0 -and $r) { return $r }
  }
  return (Get-Here)
}
function Get-AdlcDir {
  if ($env:ADLC_DOCS_DIR) { return (Resolve-Abs $env:ADLC_DOCS_DIR) }
  return ((Get-ProjectRoot) + '/docs/adlc')
}
function Get-KeyDir([string]$key) { (Get-AdlcDir) + "/$key" }
function Get-StateFile([string]$key) { (Get-KeyDir $key) + '/state.md' }
function Get-Version {
  $f = Join-Path $ScriptDir '../VERSION'
  if (Test-Path -LiteralPath $f) { return ([IO.File]::ReadAllText($f)).Trim() }
  return 'unknown'
}

# --- files (UTF-8 without BOM, LF line endings, same bytes as the bash twin) ---
function Read-Text([string]$path) { [IO.File]::ReadAllText($path, [Text.Encoding]::UTF8) }
function Write-Text([string]$path, [string]$text) {
  $text = $text -replace "`r`n", "`n"
  [IO.File]::WriteAllText($path, $text, $Utf8NoBom)
}
function Read-Lines([string]$path) {
  $t = (Read-Text $path) -replace "`r", ''
  if ($t.EndsWith("`n")) { $t = $t.Substring(0, $t.Length - 1) }
  return , ($t -split "`n")
}
function Write-Lines([string]$path, [string[]]$lines) { Write-Text $path (($lines -join "`n") + "`n") }

function Expand-Template([string]$name, [hashtable]$vars) {
  $t = (Read-Text (Join-Path $Templates $name)) -replace "`r", ''
  foreach ($k in $vars.Keys) { $t = $t.Replace($k, [string]$vars[$k]) }   # literal, no regex
  if (-not $t.EndsWith("`n")) { $t += "`n" }
  return $t
}

# --- validation ----------------------------------------------------------------
function Test-Key([string]$key) { return ($key -cmatch $KeyRe) }
function Assert-Key([string]$key) {
  if (-not (Test-Key $key)) { Fail "invalid KEY '$key' (expected e.g. ADLC-001 or PROJ-123)" }
}
function Assert-Run([string]$key) {
  Assert-Key $key
  $sf = Get-StateFile $key
  if (-not (Test-Path -LiteralPath $sf)) {
    Fail "no ADLC run for $key (expected $sf); start one with: adlc init `"<request>`""
  }
}
function ConvertTo-OneLine([string]$s) { return ($s -replace "[`r`n`t]", ' ') }

# --- optional .env (JIRA_* / ADLC_* only; never overrides; never evaluated) ----
function Import-DotEnv {
  foreach ($f in @(((Get-ProjectRoot) + '/.env'), (Join-Path $ScriptDir '../../.env'))) {
    if (-not (Test-Path -LiteralPath $f)) { continue }
    foreach ($line in (Read-Lines $f)) {
      $line = $line -replace '^export ', ''
      if ($line -notmatch '^\s*((JIRA|ADLC)_[A-Z0-9_]+)\s*=(.*)$') { continue }
      $k = $Matches[1]; $v = $Matches[3].Trim()
      if ($v.Length -ge 2 -and (($v[0] -eq '"' -and $v[-1] -eq '"') -or ($v[0] -eq "'" -and $v[-1] -eq "'"))) {
        $v = $v.Substring(1, $v.Length - 2)
      }
      if ($null -eq [Environment]::GetEnvironmentVariable($k)) { [Environment]::SetEnvironmentVariable($k, $v) }
    }
  }
}

function Get-Python {
  foreach ($c in @('python3', 'py', 'python')) {
    if (-not (Get-Command $c -ErrorAction SilentlyContinue)) { continue }
    $null = Invoke-Native $c @('-c', 'import sys; assert sys.version_info >= (3, 8)') -Quiet
    if ($script:NativeCode -eq 0) { return $c }
  }
  return $null
}

# --- state.md ------------------------------------------------------------------
# Field lines look like "- <field>: <value>" and sit above "## Log".
function Get-StateValue([string]$key, [string]$field) {
  if ($field -cnotmatch $FieldRe) { Fail "invalid state field '$field'" }
  $sf = Get-StateFile $key
  if (-not (Test-Path -LiteralPath $sf)) { return '' }
  $p = "- ${field}:"
  foreach ($line in (Read-Lines $sf)) {
    if ($line.StartsWith('## ')) { break }
    if ($line.StartsWith($p)) { return $line.Substring($p.Length).TrimStart() }
  }
  return ''
}

function Set-StateValue([string]$key, [string]$field, [string]$value) {
  $sf = Get-StateFile $key
  if (-not (Test-Path -LiteralPath $sf)) { Fail "no state file for $key (run: adlc init)" }
  if ($field -cnotmatch $FieldRe) { Fail "invalid state field '$field' (use lowercase letters, digits, _)" }
  $p = "- ${field}:"
  $newLine = "$p $(ConvertTo-OneLine $value)"
  $lines = Read-Lines $sf
  $found = -1; $last = -1
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i].StartsWith('## ')) { break }
    if ($found -lt 0 -and $lines[$i].StartsWith($p)) { $found = $i }
    if ($lines[$i] -cmatch '^- [a-z0-9_]+:') { $last = $i }
  }
  $out = New-Object System.Collections.Generic.List[string]
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($i -eq $found) { $out.Add($newLine); continue }
    $out.Add($lines[$i])
    if ($found -lt 0 -and $i -eq $last) { $out.Add($newLine) }
  }
  if ($found -lt 0 -and $last -lt 0) { $out.Add($newLine) }
  Write-Lines $sf $out.ToArray()
}

function Add-StateLog([string]$key, [string]$msg) {
  $sf = Get-StateFile $key
  $line = "- $(Get-Date -Format 'yyyy-MM-dd') $(ConvertTo-OneLine $msg)`n"
  [IO.File]::AppendAllText($sf, $line, $Utf8NoBom)
}

# --- git -----------------------------------------------------------------------
function Assert-GitRepo {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail 'git not found on PATH' }
  $null = Invoke-Git @('rev-parse', '--is-inside-work-tree') -Quiet
  if ($script:NativeCode -ne 0) { Fail 'not inside a git repository (run: git init)' }
}
function Get-CurrentBranch { Invoke-Git @('symbolic-ref', '--quiet', '--short', 'HEAD') -Quiet }
function Test-ProtectedBranch([string]$b) { return @('main', 'master', 'develop', 'trunk', 'production', 'release') -contains $b }
function Test-BranchName([string]$b) {
  $null = Invoke-Git @('check-ref-format', '--branch', $b) -Quiet
  return ($script:NativeCode -eq 0)
}
function Switch-ToBranch([string]$b) {
  if (-not (Test-BranchName $b)) { Fail "invalid branch name '$b'" }
  if (Test-ProtectedBranch $b) { Fail "refusing to use protected branch '$b' as a feature branch" }
  if ((Get-CurrentBranch) -eq $b) { return }
  $null = Invoke-Git @('show-ref', '--verify', '--quiet', "refs/heads/$b") -Quiet
  if ($script:NativeCode -eq 0) {
    if ((Invoke-Passthrough 'git' @('checkout', '-q', $b, '--')) -ne 0) { Fail "could not switch to $b (uncommitted changes in the way?)" }
  } else {
    if ((Invoke-Passthrough 'git' @('checkout', '-q', '-b', $b)) -ne 0) { Fail "could not create branch $b" }
  }
}

function Get-Slug([string]$text) {
  $s = ($text.ToLowerInvariant() -replace '[^a-z0-9]+', '-').Trim('-')
  $s = (($s -split '-') | Select-Object -First 6) -join '-'
  if ($s.Length -gt 50) { $s = $s.Substring(0, 50) }
  $s = $s.TrimEnd('-')
  if (-not $s) { $s = 'change' }
  return $s
}

function Get-NextKey {
  $d = Get-AdlcDir; $max = 0
  $names = @()
  if (Test-Path -LiteralPath "$d/tickets") { $names += @(Get-ChildItem -LiteralPath "$d/tickets" -Filter 'ADLC-*.md' | ForEach-Object { $_.BaseName }) }
  if (Test-Path -LiteralPath $d) { $names += @(Get-ChildItem -LiteralPath $d -Filter 'ADLC-*' | ForEach-Object { $_.Name -replace '\.md$', '' }) }
  foreach ($n in $names) {
    if ($n -match '^ADLC-(\d+)$') { $v = [int]$Matches[1]; if ($v -gt $max) { $max = $v } }
  }
  return ('ADLC-{0:D3}' -f ($max + 1))
}

function Get-CompareUrl([string]$branch) {
  $remote = if ($env:ADLC_REMOTE) { $env:ADLC_REMOTE } else { 'origin' }
  $url = Invoke-Git @('remote', 'get-url', $remote) -Quiet
  if ($script:NativeCode -ne 0 -or -not $url) { return '' }
  $url = $url.TrimEnd('/') -replace '\.git$', ''
  if ($url -match '^(https?|ssh|git)://([^/]+)/(.+)$') {
    $scheme = $Matches[1]; $hostpart = $Matches[2]; $path = $Matches[3]
    $hostpart = $hostpart -replace '^.*@', ''           # drop user:token@ (never print credentials)
    if ($scheme -eq 'http' -or $scheme -eq 'https') { $h = $hostpart }
    else { $h = ($hostpart -split ':')[0]; $scheme = 'https' }
  } elseif ($url -match '^[^/@]+@([^:/]+):(.+)$') {
    $scheme = 'https'; $h = $Matches[1]; $path = $Matches[2]
  } else { return '' }
  $base = "${scheme}://$h/$path"
  if ($h -match 'gitlab') { return "$base/-/merge_requests/new?merge_request%5Bsource_branch%5D=$branch" }
  if ($h -match 'bitbucket') { return "$base/pull-requests/new?source=$branch" }
  return "$base/compare/$branch" + '?expand=1'
}

# Detected project stack(s) from marker files at the project root.
# Keep in sync with detect_stack in lib.sh.
function Get-Stack {
  $root = Get-ProjectRoot
  $has = { param($n) Test-Path -LiteralPath (Join-Path $root $n) }
  $f = @()
  if (& $has 'pom.xml') { $f += 'java-maven' }
  if ((& $has 'build.gradle') -or (& $has 'build.gradle.kts')) {
    $android = $false
    foreach ($g in @('build.gradle', 'build.gradle.kts', 'settings.gradle', 'settings.gradle.kts')) {
      if ((& $has $g) -and ((Read-Text (Join-Path $root $g)) -cmatch 'com\.android')) { $android = $true }
    }
    if (-not $android) {
      $m = Get-ChildItem -LiteralPath $root -Recurse -Depth 3 -Filter 'AndroidManifest.xml' -ErrorAction SilentlyContinue | Select-Object -First 1
      $android = ($null -ne $m)
    }
    if ($android) { $f += 'android' } else { $f += 'java-gradle' }
  }
  if (& $has 'package.json') {
    $pkg = Read-Text (Join-Path $root 'package.json')
    if ($pkg -cmatch '"react"') { $f += 'react' }
    elseif ($pkg -cmatch '"vue"') { $f += 'vue' }
    elseif ($pkg -cmatch '"@angular/core"') { $f += 'angular' }
    else { $f += 'node' }
  }
  if ((& $has 'pyproject.toml') -or (& $has 'setup.py') -or (& $has 'requirements.txt')) { $f += 'python' }
  if (& $has 'go.mod') { $f += 'go' }
  if (& $has 'Cargo.toml') { $f += 'rust' }
  if (& $has 'Gemfile') { $f += 'ruby' }
  if (& $has 'composer.json') { $f += 'php' }
  $dn = @(Get-ChildItem -LiteralPath $root -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -eq '.csproj' -or $_.Extension -eq '.sln' })
  if ($dn.Count -gt 0) { $f += 'dotnet' }
  if ($f.Count -gt 0) { return ($f -join ' ') }
  return 'unknown'
}

# Coverage floor: ADLC_MIN_COVERAGE (0-100) if valid, else 90.
function Get-MinCoverage {
  $v = $env:ADLC_MIN_COVERAGE
  if (-not $v) { return '90' }
  if ($v -match '^[0-9]+$' -and [long]$v -le 100) { return ([string][int]$v) }
  [Console]::Error.WriteLine("adlc: ignoring ADLC_MIN_COVERAGE='$v' (expected 0-100); using 90")
  return '90'
}

function Get-VerificationResult([string]$path) {
  foreach ($line in (Read-Lines $path)) {
    if ($line -match 'Result:') { return (($line -replace '[*_` \t-]', '').ToUpperInvariant()) }
  }
  return ''
}

# --- commands --------------------------------------------------------------------
function Invoke-Ship([string[]]$a) {
  if ($a.Count -lt 1) { UsageError 'ship needs a KEY' }
  $key = $a[0]; $push = $true
  foreach ($o in @($a | Select-Object -Skip 1)) {
    if ($o -eq '--no-push') { $push = $false } else { UsageError "unknown ship option: $o" }
  }
  Assert-Run $key; Assert-GitRepo

  if ((Get-StateValue $key 'gate2_push_approved') -ne 'true') { Fail "gate2 not approved for $key (run: adlc approve $key gate2)" }
  $vf = (Get-KeyDir $key) + '/verification.md'
  if (-not (Test-Path -LiteralPath $vf)) { Fail "no verification report at $vf; run the verify stage first" }
  $result = Get-VerificationResult $vf
  if ($result -ne 'RESULT:PASS') {
    $shown = if ($result) { $result } else { 'nothing' }
    Fail "verification for $key is not PASS (found '$shown' in $vf)"
  }

  $b = Get-StateValue $key 'branch'
  if (-not $b) { Fail "no branch recorded for $key" }
  Switch-ToBranch $b

  $null = Invoke-Git @('add', '-A') -Quiet
  if ($script:NativeCode -ne 0) { Fail 'git add failed' }
  $staged = @((Invoke-Git @('diff', '--cached', '--name-only') -Quiet) -split "`n" | Where-Object { $_ })
  $flagged = @($staged | Where-Object { $_ -match $SecretRe -and $_ -notmatch $SecretOkRe })
  if ($flagged.Count -gt 0) {
    foreach ($f in $flagged) { $null = Invoke-Git @('reset', '-q', '--', $f) -Quiet }
    Fail ("refusing to commit files that look like secrets:`n" + ($flagged -join "`n") +
      "`nAdd them to .gitignore (or commit them yourself if they are safe), then re-run: adlc ship $key")
  }

  # Record the outcome *before* committing so the commit carries the final
  # state and the working tree is clean afterwards.
  Set-StateValue $key 'current_stage' 'done'
  Add-StateLog $key "ship: committed on $b"
  $null = Invoke-Git @('add', '-A') -Quiet
  $staged = @((Invoke-Git @('diff', '--cached', '--name-only') -Quiet) -split "`n" | Where-Object { $_ })

  if ($staged.Count -eq 0) {
    "adlc: nothing new to commit on $b"
  } else {
    $title = Get-StateValue $key 'title'
    $msgFile = [IO.Path]::GetTempFileName()   # -F avoids native-argument quoting bugs
    try {
      Write-Text $msgFile "${key}: $title`n`nRefs: docs/adlc/$key/spec.md`n"
      $code = Invoke-Passthrough 'git' @('commit', '-q', '-F', $msgFile)
    } finally { Remove-Item -LiteralPath $msgFile -ErrorAction SilentlyContinue }
    if ($code -ne 0) {
      Set-StateValue $key 'current_stage' 'ship'
      Add-StateLog $key 'ship: commit FAILED'
      Fail 'git commit failed (pre-commit hook or missing user.name/user.email?); changes are still staged'
    }
    "committed $($staged.Count) file(s)"
  }
  $sha = Invoke-Git @('rev-parse', '--short', 'HEAD') -Quiet

  $remote = if ($env:ADLC_REMOTE) { $env:ADLC_REMOTE } else { 'origin' }
  $null = Invoke-Git @('remote', 'get-url', $remote) -Quiet
  $hasRemote = ($script:NativeCode -eq 0)
  if ($push -and $hasRemote) {
    if ((Invoke-Passthrough 'git' @('push', '-u', $remote, $b)) -eq 0) {
      "pushed $sha to $remote/$b"
      $url = Get-CompareUrl $b
      if ($url) { "PR: $url" }
    } else {
      # The commit is safe locally. Put the stage back to ship so resume retries
      # the push (this leaves state.md modified; the retry commits it).
      Set-StateValue $key 'current_stage' 'ship'
      Add-StateLog $key "ship: push FAILED; local commit $sha kept"
      Fail "push FAILED - commit $sha kept locally on $b. Fix the remote/auth, then re-run: adlc ship $key" 3
    }
  } else {
    "committed locally only (no '$remote' remote or --no-push): $sha on $b"
  }
}

function Invoke-Doctor {
  $ok = $true
  "adlc $(Get-Version)  ($ScriptDir)"
  "shell     PowerShell $($PSVersionTable.PSVersion)"
  if (Get-Command git -ErrorAction SilentlyContinue) { "git       " + ((Invoke-Git @('--version') -Quiet) -replace '^git version ', '') }
  else { 'git       MISSING (required)'; $ok = $false }
  $py = Get-Python
  if ($py) { "python    $((Invoke-Native $py @('-c', 'import sys; print(sys.version.split()[0])') -Quiet)) ($py)" }
  else { 'python    not found (only needed for Jira mode)' }
  $null = Invoke-Git @('rev-parse', '--is-inside-work-tree') -Quiet
  if ($script:NativeCode -eq 0) {
    "project   $(Get-ProjectRoot)"
    $r = Invoke-Git @('remote', 'get-url', $(if ($env:ADLC_REMOTE) { $env:ADLC_REMOTE } else { 'origin' })) -Quiet
    if ($r) { "remote    " + ($r -replace '://[^/@]*@', '://') } else { 'remote    none' }
  } else { 'project   not a git repository (adlc branch/ship need one)' }
  if ($env:JIRA_BASE_URL -and $env:JIRA_EMAIL -and $env:JIRA_API_TOKEN) {
    $proj = if ($env:JIRA_PROJECT_KEY) { $env:JIRA_PROJECT_KEY } else { 'ADLC' }
    "jira      configured ($env:JIRA_BASE_URL, project $proj)"
  } else { 'jira      not configured -> local ticket mode' }
  if (-not $ok) { exit 1 }
}

# --- dispatch --------------------------------------------------------------------
$argv = @($args)
$cmd = if ($argv.Count -ge 1) { [string]$argv[0] } else { 'help' }
$rest = @($argv | Select-Object -Skip 1 | ForEach-Object { [string]$_ })
Import-DotEnv

switch -CaseSensitive ($cmd) {
  { $_ -in @('help', '-h', '--help') } { Show-Usage; break }
  { $_ -in @('version', '-v', '--version') } { "adlc $(Get-Version)"; break }
  'next-key' { Get-NextKey; break }

  'jira' {
    $py = Get-Python
    if (-not $py) { Fail 'no working Python 3.8+ found (tried python3, py, python)' }
    exit (Invoke-Passthrough $py (@((Join-Path $ScriptDir 'jira_ticket.py')) + $rest))
  }

  'init' {
    if ($rest.Count -lt 1 -or -not $rest[0]) { UsageError 'init needs a request: adlc init "<request>" [KEY]' }
    $req = ConvertTo-OneLine $rest[0]
    $key = if ($rest.Count -ge 2) { $rest[1] } else { Get-NextKey }
    Assert-Key $key
    $sf = Get-StateFile $key
    if (Test-Path -LiteralPath $sf) { Fail "run $key already exists ($sf); use: adlc status $key" }
    $kd = Get-KeyDir $key; $td = (Get-AdlcDir) + '/tickets'
    New-Item -ItemType Directory -Force -Path $kd, $td | Out-Null
    $today = Get-Date -Format 'yyyy-MM-dd'
    $prefix = if ($env:ADLC_BRANCH_PREFIX) { $env:ADLC_BRANCH_PREFIX } else { 'adlc' }
    $branch = "$prefix/$key-$(Get-Slug $req)"
    if ((Get-Command git -ErrorAction SilentlyContinue) -and -not (Test-BranchName $branch)) {
      Fail "invalid branch name '$branch' (check ADLC_BRANCH_PREFIX)"
    }
    Write-Text $sf (Expand-Template 'state.md' @{ '<KEY>' = $key; '<TITLE>' = $req; '<DATE>' = $today; '<BRANCH>' = $branch })
    $ticket = Expand-Template 'ticket.md' @{ '<KEY>' = $key; '<TITLE>' = $req; '<DATE>' = $today }
    Write-Text "$kd/ticket.md" $ticket
    Write-Text "$td/$key.md" $ticket
    $key
    break
  }

  'constitution' {
    $d = Get-AdlcDir; $cfile = "$d/constitution.md"
    if (-not (Test-Path -LiteralPath $cfile)) {
      New-Item -ItemType Directory -Force -Path $d | Out-Null
      Write-Text $cfile (Expand-Template 'constitution.md' @{ '<DATE>' = (Get-Date -Format 'yyyy-MM-dd') })
      [Console]::Error.WriteLine("adlc: created $cfile - edit it to set your project's principles")
    }
    $cfile
    break
  }

  'clarifications' {
    # A real marker carries the question after a colon; the bare form in template prose is guidance.
    if ($rest.Count -lt 1) { UsageError 'clarifications needs a KEY' }
    $key = $rest[0]; Assert-Run $key; $found = $false
    foreach ($n in @('ticket', 'spec', 'tasks')) {
      $f = (Get-KeyDir $key) + "/$n.md"
      if (-not (Test-Path -LiteralPath $f)) { continue }
      $lines = Read-Lines $f
      for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Contains('[NEEDS CLARIFICATION:')) { $found = $true; "${f}:$($i + 1):$($lines[$i])" }
      }
    }
    if ($found) { exit 1 }
    "no open clarifications for $key"
    break
  }

  'detect-stack' { Get-Stack; break }
  'min-coverage' { Get-MinCoverage; break }

  'status' {
    if ($rest.Count -lt 1) { UsageError 'status needs a KEY' }
    Assert-Run $rest[0]
    (Read-Lines (Get-StateFile $rest[0]))
    break
  }
  'get-state' {
    if ($rest.Count -lt 2) { UsageError 'get-state needs <KEY> <field>' }
    Assert-Key $rest[0]; Get-StateValue $rest[0] $rest[1]; break
  }
  'set-state' {
    if ($rest.Count -lt 3) { UsageError 'set-state needs <KEY> <field> <value>' }
    Assert-Run $rest[0]; Set-StateValue $rest[0] $rest[1] $rest[2]; 'ok'; break
  }

  'approve' {
    if ($rest.Count -lt 2) { UsageError 'approve needs <KEY> gate1|gate2' }
    $key = $rest[0]; $gate = $rest[1]; Assert-Run $key
    if ($gate -ceq 'gate1') { Set-StateValue $key 'gate1_spec_approved' 'true' }
    elseif ($gate -ceq 'gate2') { Set-StateValue $key 'gate2_push_approved' 'true' }
    else { UsageError 'gate must be gate1 or gate2' }
    Add-StateLog $key "${gate}: approved by user"
    "recorded $gate approval for $key"
    break
  }

  'scaffold' {
    if ($rest.Count -lt 2) { UsageError 'scaffold needs <KEY> spec|tasks|verification' }
    $key = $rest[0]; $kind = $rest[1]; Assert-Run $key
    if (@('spec', 'tasks', 'verification') -cnotcontains $kind) { UsageError 'scaffold kind must be spec, tasks or verification' }
    $force = ($rest.Count -ge 3 -and $rest[2] -eq '--force')
    $out = (Get-KeyDir $key) + "/$kind.md"
    if ((Test-Path -LiteralPath $out) -and -not $force) { "$out (exists, left unchanged)"; break }
    $attempts = 0
    [void][int]::TryParse((Get-StateValue $key 'verify_attempts'), [ref]$attempts)
    Write-Text $out (Expand-Template "$kind.md" @{
        '<KEY>' = $key; '<TITLE>' = (Get-StateValue $key 'title')
        '<DATE>' = (Get-Date -Format 'yyyy-MM-dd'); '<N>' = ($attempts + 1) })
    $out
    break
  }

  'branch' {
    if ($rest.Count -lt 1) { UsageError 'branch needs a KEY' }
    $key = $rest[0]; Assert-Run $key; Assert-GitRepo
    $b = Get-StateValue $key 'branch'
    if (-not $b) { Fail "no branch recorded for $key" }
    Switch-ToBranch $b
    $b
    break
  }

  'compare-url' {
    if ($rest.Count -lt 1) { UsageError 'compare-url needs a branch' }
    Get-CompareUrl $rest[0]; break
  }

  'ship' { Invoke-Ship $rest; break }
  'doctor' { Invoke-Doctor; break }
  default { UsageError "unknown command: $cmd" }
}
# Explicit success: otherwise $LASTEXITCODE would leak from the last git probe.
exit 0
