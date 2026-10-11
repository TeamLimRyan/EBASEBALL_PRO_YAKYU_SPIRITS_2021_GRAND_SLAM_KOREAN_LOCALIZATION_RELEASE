@echo off
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply_patch.ps1" %*
set "result=%ERRORLEVEL%"
pause
exit /b %result%
