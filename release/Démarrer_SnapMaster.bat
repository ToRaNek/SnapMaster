@echo off
echo D�marrage de SnapMaster...
start "" "%~dp0SnapMaster.exe"
echo SnapMaster d�marr� en arri�re-plan
timeout /t 2 /nobreak >nul
