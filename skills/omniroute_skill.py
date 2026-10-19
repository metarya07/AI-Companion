"""OmniRoute Gateway & Claude Code Agent Launcher Skill.

Provides control over the OmniRoute local gateway (port 20128) and enables
launching Claude Code sessions with custom model profiles.
"""

from __future__ import annotations

import os
import socket
import subprocess
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional, Tuple

from config.settings import Settings
from core.registry import Skill
from core.types import ParsedCommand


def is_omniroute_online(host: str = "127.0.0.1", port: int = 20128, timeout: float = 1.0) -> bool:
    """Check if the OmniRoute TCP port is accepting connections."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        sock.close()
        return True
    except (socket.error, OSError):
        return False


def get_claude_executable() -> str:
    """Find Claude executable path in Windows user environment or PATH."""
    home = os.path.expanduser("~")
    winget_pkg = os.path.join(
        home,
        "AppData",
        "Local",
        "Microsoft",
        "WinGet",
        "Packages",
        "Anthropic.ClaudeCode_Microsoft.Winget.Source_8wekyb3d8bbwe",
        "claude.exe",
    )
    if os.path.isfile(winget_pkg):
        return winget_pkg
    return "claude"


class OmniRouteSkill(Skill):
    name = "OmniRoute"
    triggers = ("omniroute", "claude")
    help = (
        ("omniroute [status]", "Check if OmniRoute server is online on port 20128"),
        ("omniroute start", "Start the OmniRoute background server"),
        ("omniroute sync", "Sync Claude profiles with OmniRoute"),
        ("omniroute web", "Open the OmniRoute & Agent Desktop Manager web GUI"),
        ("claude [profile] [path]", "Launch a Claude Code terminal session (default: auto-best-free)"),
    )

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def handle(self, command: ParsedCommand) -> str:
        verb = (command.verb or "").lower()
        args = (command.args or "").strip()

        if verb == "claude":
            return self._handle_claude(args)

        # Verb is 'omniroute'
        tokens = args.split()
        subcmd = tokens[0].lower() if tokens else "status"
        subargs = " ".join(tokens[1:]) if len(tokens) > 1 else ""

        if subcmd in ("status", "check"):
            return self._handle_status()
        if subcmd == "start":
            return self._handle_start()
        if subcmd == "sync":
            return self._handle_sync()
        if subcmd in ("web", "ui", "dashboard", "app"):
            return self._handle_web()
        if subcmd == "launch":
            return self._handle_claude(subargs)

        return (
            f"Unknown omniroute action '{subcmd}'. "
            "Available: omniroute status, omniroute start, omniroute sync, omniroute web, claude [profile]."
        )

    def _handle_status(self) -> str:
        online = is_omniroute_online()
        if online:
            # Try getting profile / model count
            model_count = "unknown"
            try:
                req = urllib.request.Request("http://localhost:20128/v1/models")
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    import json
                    data = json.loads(resp.read().decode("utf-8"))
                    model_count = str(len(data.get("data", [])))
            except Exception:
                pass
            return (
                "OmniRoute Status: ONLINE\n"
                "  * Endpoint: http://localhost:20128/v1\n"
                f"  * Active Models: {model_count}\n"
                "  * Web GUI: http://localhost:42100 (run 'omniroute web')"
            )
        return (
            "OmniRoute Status: OFFLINE\n"
            "  * Port 20128 is not reachable.\n"
            "  * Run 'omniroute start' or double-click launchers/Launch-OmniRoute-Manager.bat to start it."
        )

    def _handle_start(self) -> str:
        if is_omniroute_online():
            return "OmniRoute is already running on port 20128."

        if self.settings.dry_run:
            return "DRY RUN: would start OmniRoute background process (powershell omniroute serve)."

        try:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "/min", "powershell", "-NoExit", "-Command", "omniroute serve"],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
            return "Starting OmniRoute in the background... It will be ready on http://localhost:20128 in a few seconds."
        except Exception as exc:
            return f"Failed to start OmniRoute: {exc}"

    def _handle_sync(self) -> str:
        if self.settings.dry_run:
            return "DRY RUN: would run 'omniroute setup-claude' to sync profiles."

        try:
            result = subprocess.run(
                ["omniroute", "setup-claude"],
                capture_output=True,
                text=True,
                shell=(os.name == "nt"),
                timeout=30,
            )
            output = (result.stdout or result.stderr or "").strip()
            return output or "OmniRoute profiles synced successfully."
        except Exception as exc:
            return f"Failed to sync OmniRoute profiles: {exc}"

    def _handle_web(self) -> str:
        if self.settings.dry_run:
            return "DRY RUN: would launch OmniRoute Web Manager on port 42100."

        app_dir = Path(self.settings.db_path).parent / "tools" / "omniroute-app"
        server_script = app_dir / "server.js"

        if server_script.is_file():
            try:
                subprocess.Popen(
                    ["cmd.exe", "/c", "start", "node", str(server_script)],
                    cwd=str(app_dir),
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                )
                webbrowser.open("http://localhost:42100")
                return "Launched OmniRoute Web Manager dashboard at http://localhost:42100."
            except Exception:
                webbrowser.open("http://localhost:42100")
                return "Opened http://localhost:42100 in your browser."

        webbrowser.open("http://localhost:42100")
        return "Opened http://localhost:42100 in your browser."

    def _handle_claude(self, args: str) -> str:
        tokens = args.split(maxsplit=1) if args else []
        profile = tokens[0] if tokens else self.settings.omniroute_model
        project_dir = tokens[1] if len(tokens) > 1 else str(Path(self.settings.db_path).parent)

        if self.settings.dry_run:
            return f"DRY RUN: would launch Claude Code with profile '{profile}' in '{project_dir}'."

        # Start OmniRoute if not running
        if not is_omniroute_online():
            self._handle_start()

        claude_exe = get_claude_executable()
        profile_dir = os.path.expanduser(f"~/.claude/profiles/{profile}")

        ps_command = (
            f"$Host.UI.RawUI.WindowTitle = 'Claude Code [{profile}]'; "
            f"$env:CLAUDE_CONFIG_DIR = '{profile_dir}'; "
            f"$env:ANTHROPIC_BASE_URL = 'http://localhost:20128'; "
            f"$env:ANTHROPIC_AUTH_TOKEN = 'dummy'; "
            "Remove-Item env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue; "
            f"Set-Location -Path '{project_dir}'; "
            "Write-Host '==================================================' -ForegroundColor Cyan; "
            "Write-Host '  JARVIS Coding Agent Launcher' -ForegroundColor Green; "
            f"Write-Host '  Profile:   {profile}' -ForegroundColor Yellow; "
            f"Write-Host '  Directory: {project_dir}' -ForegroundColor Yellow; "
            "Write-Host '  Gateway:   http://localhost:20128' -ForegroundColor Yellow; "
            "Write-Host '==================================================' -ForegroundColor Cyan; "
            "Write-Host ''; "
            f"& '{claude_exe}'"
        )

        try:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "powershell", "-NoExit", "-Command", ps_command],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
            return f"Launched Claude Code [{profile}] in a new terminal window ({project_dir})."
        except Exception as exc:
            return f"Failed to launch Claude Code: {exc}"
