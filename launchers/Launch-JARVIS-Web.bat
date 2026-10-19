@echo off
title JARVIS Web Dashboard
cd /d "%~dp0.."

set "JARVIS_AI_PROVIDER=omniroute"

if exist "%~dp0..\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0..\venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

start "" http://localhost:5050
"%PYTHON_EXE%" main.py --app --no-browser
pause
