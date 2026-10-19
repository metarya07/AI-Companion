@echo off
title JARVIS - OmniRoute & Claude Code Manager
cd /d "%~dp0"

echo ========================================================
echo   Starting OmniRoute & Claude Code Desktop Manager...
echo ========================================================

start "" http://localhost:42100
node server.js
pause
