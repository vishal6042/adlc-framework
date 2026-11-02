@echo off
REM Windows shim so `adlc` works from cmd.exe. It runs the PowerShell twin
REM (adlc.ps1) rather than `bash`, because on Windows a bare `bash` is often
REM WSL's bash.exe, which cannot see Windows paths the same way.
REM Git Bash users get the bash `adlc` script directly (it is found first there).
setlocal
where pwsh >nul 2>nul
if %errorlevel%==0 (
  pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0adlc.ps1" %*
) else (
  powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0adlc.ps1" %*
)
exit /b %errorlevel%
