@echo off
echo Démarrage de SnapMaster...
start "" "%~dp0SnapMaster.exe"
echo SnapMaster démarré en arrière-plan
timeout /t 2 /nobreak >nul
