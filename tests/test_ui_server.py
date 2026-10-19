"""Tests for JARVIS Web App UI server & API endpoints."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from typing import Tuple

import pytest

from config.settings import Settings
from apps.web.server import create_app_server


@pytest.fixture
def running_server(tmp_path) -> Tuple[str, ThreadingHTTPServer]:
    db_file = tmp_path / "test_jarvis_ui.db"
    settings = Settings(db_path=db_file, dry_run=True, ai_provider="none")
    # Bind to port 0 for automatic available port selection
    server = create_app_server(settings, host="127.0.0.1", port=0)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield base_url

    server.shutdown()


def _request_json(url: str, method: str = "GET", payload: dict = None) -> Tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(body)
        except Exception:
            return exc.code, {"error": body}


def test_status_endpoint(running_server):
    status, data = _request_json(f"{running_server}/api/status")
    assert status == 200
    assert "version" in data
    assert "system" in data
    assert data["ai_provider"] == "none"


def test_command_endpoint(running_server):
    status, data = _request_json(
        f"{running_server}/api/command", method="POST", payload={"command": "time"}
    )
    assert status == 200
    assert "Current time:" in data.get("response", "")


def test_command_empty_error(running_server):
    status, data = _request_json(
        f"{running_server}/api/command", method="POST", payload={"command": ""}
    )
    assert status == 400
    assert "error" in data


def test_tasks_crud(running_server):
    # Add task
    status, data = _request_json(
        f"{running_server}/api/tasks", method="POST", payload={"text": "Write code", "due": "tomorrow"}
    )
    assert status == 200
    task_id = data["id"]

    # List tasks
    status, tasks = _request_json(f"{running_server}/api/tasks?all=1")
    assert status == 200
    assert any(t["id"] == task_id and t["text"] == "Write code" for t in tasks)

    # Toggle task
    status, toggle_data = _request_json(
        f"{running_server}/api/tasks/toggle", method="POST", payload={"id": task_id}
    )
    assert status == 200
    assert toggle_data["now_done"] is True

    # Delete task
    status, del_data = _request_json(
        f"{running_server}/api/tasks", method="DELETE", payload={"id": task_id}
    )
    assert status == 200
    assert del_data["success"] is True


def test_notes_crud(running_server):
    # Add note
    status, data = _request_json(
        f"{running_server}/api/notes", method="POST", payload={"text": "Remember secret code"}
    )
    assert status == 200
    note_id = data["id"]

    # Search notes
    status, notes = _request_json(f"{running_server}/api/notes?q=secret")
    assert status == 200
    assert any(n["id"] == note_id for n in notes)

    # Delete note
    status, del_data = _request_json(
        f"{running_server}/api/notes", method="DELETE", payload={"id": note_id}
    )
    assert status == 200
    assert del_data["success"] is True


def test_prefs_crud(running_server):
    # Set pref
    status, data = _request_json(
        f"{running_server}/api/prefs", method="POST", payload={"key": "theme", "value": "cyan"}
    )
    assert status == 200

    # Get prefs
    status, prefs = _request_json(f"{running_server}/api/prefs")
    assert status == 200
    assert prefs.get("theme") == "cyan"

    # Delete pref
    status, del_data = _request_json(
        f"{running_server}/api/prefs", method="DELETE", payload={"key": "theme"}
    )
    assert status == 200
    assert del_data["success"] is True


def test_static_file_serving(running_server):
    req = urllib.request.Request(f"{running_server}/")
    with urllib.request.urlopen(req, timeout=3.0) as resp:
        assert resp.status == 200
        content = resp.read().decode("utf-8")
        assert "<title>JARVIS" in content
