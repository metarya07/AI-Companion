@echo off
title JARVIS Command Line Interface
cd /d "%~dp0.."

set "JARVIS_AI_PROVIDER=omniroute"

if exist "%~dp0..\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0..\venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" main.py
pause
