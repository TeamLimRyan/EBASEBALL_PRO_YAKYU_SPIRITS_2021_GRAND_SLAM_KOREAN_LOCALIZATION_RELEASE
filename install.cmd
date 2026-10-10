@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply_patch.ps1" %*
exit /b %errorlevel%
