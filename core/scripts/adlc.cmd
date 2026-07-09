@echo off
REM Windows shim so `adlc` is callable from cmd.exe / PowerShell as well as Git Bash.
REM Routes to the bash implementation (Git Bash ships with Git for Windows).
setlocal
where bash >nul 2>nul
if %errorlevel%==0 (
  bash "%~dp0adlc" %*
) else (
  echo adlc: bash not found on PATH. Install Git for Windows, or call adlc.ps1 for the subset of commands it supports.>&2
  exit /b 1
)
