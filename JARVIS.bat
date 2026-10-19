@echo off
title JARVIS - AI Operating Companion
cd /d "%~dp0"

set "JARVIS_AI_PROVIDER=omniroute"

if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo ========================================================
echo   Launching JARVIS Native Windows Application...
echo ========================================================

"%PYTHON_EXE%" apps/desktop/gui_app.py
pause
