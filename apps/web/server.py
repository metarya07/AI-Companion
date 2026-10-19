"""JARVIS Desktop Application Web Server & API Layer.

Provides a unified REST API for the JARVIS Brain, memory database, live
system telemetry, planning agent, OmniRoute gateway, and serves the
futuristic JARVIS HUD frontend.
"""

from __future__ import annotations

import json
import mimetypes
import os
import socket
import subprocess
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root is on sys.path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from core import __version__
from core.bootstrap import build_brain
from memory.database import Database
from memory.history import HistoryStore
from memory.prefs import PrefStore
from memory.schedules import ScheduleStore
from memory.tasks import TaskStore
from skills.omniroute_skill import is_omniroute_online, get_claude_executable

try:
    import psutil
except ImportError:
    psutil = None

PUBLIC_DIR = Path(__file__).resolve().parent / "public"


def _get_system_stats() -> Dict[str, Any]:
    """Sample current CPU, RAM, Disk, Battery, and Uptime."""
    if psutil is None:
        return {
            "cpu_percent": 0.0,
            "ram_percent": 0.0,
            "ram_used_gb": 0.0,
            "ram_total_gb": 0.0,
            "disk_percent": 0.0,
            "disk_used_gb": 0.0,
            "disk_total_gb": 0.0,
            "battery_percent": None,
            "battery_charging": None,
            "uptime_seconds": 0,
            "psutil_available": False,
        }

    try:
        cpu = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        du = psutil.disk_usage(os.path.abspath(os.sep))
        batt = psutil.sensors_battery()
        boot_time = psutil.boot_time()
        uptime = max(0, int(time.time() - boot_time))

        return {
            "cpu_percent": round(cpu, 1),
            "ram_percent": round(vm.percent, 1),
            "ram_used_gb": round(vm.used / (1024 ** 3), 1),
            "ram_total_gb": round(vm.total / (1024 ** 3), 1),
            "disk_percent": round(du.percent, 1),
            "disk_used_gb": round(du.used / (1024 ** 3), 1),
            "disk_total_gb": round(du.total / (1024 ** 3), 1),
            "battery_percent": round(batt.percent, 1) if batt else None,
            "battery_charging": batt.power_plugged if batt else None,
            "uptime_seconds": uptime,
            "psutil_available": True,
        }
    except Exception:
        return {"psutil_available": False}


class JarvisRequestHandler(BaseHTTPRequestHandler):
    settings: Settings
    brain: Any

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        db_path = self.settings.db_path

        if path == "/api/status":
            stats = _get_system_stats()
            omni_online = is_omniroute_online()
            return self._send_json({
                "version": __version__,
                "system": stats,
                "ai_provider": self.settings.ai_provider,
                "ai_model": self.settings.ai_model,
                "omniroute_online": omni_online,
                "omniroute_model": self.settings.omniroute_model,
                "workspace": str(Path(self.settings.db_path).parent),
            })

        if path == "/api/tasks":
            store = TaskStore(db_path)
            include_done = query.get("all", ["0"])[0] in ("1", "true")
            tasks = store.all(include_done=include_done)
            return self._send_json([
                {
                    "id": t.id,
                    "text": t.text,
                    "done": t.done,
                    "created_at": t.created_at,
                    "due_date": t.due,
                }
                for t in tasks
            ])

        if path == "/api/notes":
            store = Database(db_path)
            q = query.get("q", [""])[0].strip()
            notes = store.search(q) if q else store.all()
            return self._send_json([
                {"id": n.id, "text": n.text, "created_at": n.created_at}
                for n in notes
            ])

        if path == "/api/prefs":
            store = PrefStore(db_path)
            return self._send_json(dict(store.all()))

        if path == "/api/history":
            limit = int(query.get("limit", [20])[0])
            store = HistoryStore(db_path)
            turns = store.recent(limit)
            return self._send_json([
                {
                    "id": t.id,
                    "timestamp": t.timestamp,
                    "user_input": t.user_input,
                    "response": t.response,
                }
                for t in turns
            ])

        if path == "/api/schedules":
            store = ScheduleStore(db_path)
            schedules = store.all()
            return self._send_json([
                {
                    "id": s.id,
                    "command": s.command,
                    "spec": s.spec,
                    "created_at": s.created_at,
                    "last_run": s.last_run,
                }
                for s in schedules
            ])

        if path == "/api/omniroute/profiles":
            profiles_dir = Path.home() / ".claude" / "profiles"
            profiles = []
            if profiles_dir.exists():
                for d in profiles_dir.iterdir():
                    if d.is_dir():
                        name = d.name
                        is_free = "free" in name or "auto" in name
                        profiles.append({
                            "name": name,
                            "is_free": is_free,
                        })
            return self._send_json(profiles)

        # Serve static files from public/
        return self._serve_static(path)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()
        db_path = self.settings.db_path

        if path == "/api/command":
            cmd_text = body.get("command", "").strip()
            if not cmd_text:
                return self._send_json({"error": "No command provided"}, 400)
            response = self.brain.process(cmd_text)
            return self._send_json({
                "response": response.text,
                "should_exit": response.should_exit,
            })

        if path == "/api/tasks":
            text = body.get("text", "").strip()
            due = body.get("due", None)
            if not text:
                return self._send_json({"error": "Task text is required"}, 400)
            store = TaskStore(db_path)
            task_id = store.add(text, due=due)
            return self._send_json({"success": True, "id": task_id})

        if path == "/api/tasks/toggle":
            task_id = body.get("id")
            if task_id is None:
                return self._send_json({"error": "Task id is required"}, 400)
            store = TaskStore(db_path)
            from contextlib import closing
            from memory.store import connect
            with closing(connect(store.path)) as conn:
                row = conn.execute("SELECT done FROM tasks WHERE id = ?", (int(task_id),)).fetchone()
                if not row:
                    return self._send_json({"error": "Task not found"}, 404)
                new_done = 0 if row["done"] else 1
                conn.execute("UPDATE tasks SET done = ? WHERE id = ?", (new_done, int(task_id)))
                conn.commit()
            return self._send_json({"success": True, "now_done": bool(new_done)})

        if path == "/api/notes":
            text = body.get("text", "").strip()
            if not text:
                return self._send_json({"error": "Note text is required"}, 400)
            store = Database(db_path)
            note_id = store.add(text)
            return self._send_json({"success": True, "id": note_id})

        if path == "/api/prefs":
            key = body.get("key", "").strip()
            val = body.get("value", "").strip()
            if not key:
                return self._send_json({"error": "Key is required"}, 400)
            store = PrefStore(db_path)
            store.set(key, val)
            return self._send_json({"success": True})

        if path == "/api/omniroute/start":
            if is_omniroute_online():
                return self._send_json({"success": True, "message": "Already running"})
            try:
                subprocess.Popen(
                    ["cmd.exe", "/c", "start", "/min", "powershell", "-NoExit", "-Command", "omniroute"],
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                )
                return self._send_json({"success": True, "message": "Starting OmniRoute background process"})
            except Exception as exc:
                return self._send_json({"success": False, "error": str(exc)}, 500)

        if path == "/api/omniroute/launch":
            profile = body.get("profile", "auto-best-free")
            target_dir = body.get("project") or str(Path(self.settings.db_path).parent)
            claude_exe = get_claude_executable()
            profile_dir = os.path.expanduser(f"~/.claude/profiles/{profile}")

            ps_command = (
                f"$Host.UI.RawUI.WindowTitle = 'Claude Code [{profile}]'; "
                f"$env:CLAUDE_CONFIG_DIR = '{profile_dir}'; "
                f"$env:ANTHROPIC_BASE_URL = 'http://localhost:20128'; "
                f"$env:ANTHROPIC_AUTH_TOKEN = 'dummy'; "
                "Remove-Item env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue; "
                f"Set-Location -Path '{target_dir}'; "
                "Write-Host '==================================================' -ForegroundColor Cyan; "
                "Write-Host '  JARVIS Coding Agent Launcher' -ForegroundColor Green; "
                f"Write-Host '  Profile:   {profile}' -ForegroundColor Yellow; "
                f"Write-Host '  Directory: {target_dir}' -ForegroundColor Yellow; "
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
                return self._send_json({"success": True, "profile": profile, "directory": target_dir})
            except Exception as exc:
                return self._send_json({"success": False, "error": str(exc)}, 500)

        if path == "/api/vision/capture":
            resp = self.brain.process("screen")
            return self._send_json({"response": resp.text})

        return self._send_json({"error": "Not Found"}, 404)

    def do_DELETE(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()
        db_path = self.settings.db_path

        if path == "/api/notes":
            note_id = body.get("id")
            if note_id is None:
                return self._send_json({"error": "Note id is required"}, 400)
            store = Database(db_path)
            deleted = store.delete(int(note_id))
            return self._send_json({"success": deleted})

        if path == "/api/tasks":
            task_id = body.get("id")
            if task_id is None:
                return self._send_json({"error": "Task id is required"}, 400)
            store = TaskStore(db_path)
            deleted = store.delete(int(task_id))
            return self._send_json({"success": deleted})

        if path == "/api/prefs":
            key = body.get("key", "").strip()
            if not key:
                return self._send_json({"error": "Key is required"}, 400)
            store = PrefStore(db_path)
            deleted = store.delete(key)
            return self._send_json({"success": deleted})

        if path == "/api/history":
            store = HistoryStore(db_path)
            store.clear()
            return self._send_json({"success": True})

        return self._send_json({"error": "Not Found"}, 404)

    def _serve_static(self, req_path: str) -> None:
        clean_path = req_path.lstrip("/")
        if not clean_path or clean_path == "/":
            clean_path = "index.html"

        file_path = (PUBLIC_DIR / clean_path).resolve()
        if not str(file_path).startswith(str(PUBLIC_DIR.resolve())) or not file_path.is_file():
            self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        ctype, _ = mimetypes.guess_type(str(file_path))
        ctype = ctype or "application/octet-stream"

        try:
            content = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as exc:
            self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.end_headers()
            self.wfile.write(str(exc).encode("utf-8"))


def create_app_server(
    settings: Optional[Settings] = None,
    host: str = "127.0.0.1",
    port: int = 5050,
) -> ThreadingHTTPServer:
    """Create a configured ThreadingHTTPServer instance ready to serve."""
    settings = settings or Settings.from_env()
    brain = build_brain(settings)

    class CustomHandler(JarvisRequestHandler):
        pass

    CustomHandler.settings = settings
    CustomHandler.brain = brain

    server = ThreadingHTTPServer((host, port), CustomHandler)
    return server
