"""CodeSkill: scaffolding Python projects and Java classes."""

from __future__ import annotations

from config.settings import Settings
from core.types import ParsedCommand
from skills.code_skill import CodeSkill


def _cmd(raw: str) -> ParsedCommand:
    parts = raw.split(maxsplit=1)
    verb = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    return ParsedCommand(raw=raw, verb=verb, args=args)


def test_python_dry_run_lists_files():
    skill = CodeSkill(Settings(dry_run=True))
    out = skill.handle(_cmd("scaffold python my_app"))
    assert out.startswith("[dry-run] would create Python project 'my_app'")
    assert "main.py" in out and "test_my_app.py" in out


def test_python_real_creates_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    skill = CodeSkill(Settings(dry_run=False))
    out = skill.handle(_cmd("scaffold python demoapp"))
    assert "Created Python project 'demoapp'" in out
    assert (tmp_path / "demoapp" / "demoapp" / "main.py").exists()
    assert (tmp_path / "demoapp" / "tests" / "test_demoapp.py").exists()
    assert (tmp_path / "demoapp" / "README.md").exists()


def test_java_real_creates_class(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    skill = CodeSkill(Settings(dry_run=False))
    out = skill.handle(_cmd("scaffold java Student"))
    java = tmp_path / "Student.java"
    assert java.exists()
    assert "public class Student" in java.read_text()
    assert "Created Java class 'Student'" in out


def test_java_name_is_pascal_cased(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    CodeSkill(Settings(dry_run=False)).handle(_cmd("scaffold java student record"))
    assert (tmp_path / "StudentRecord.java").exists()


def test_refuses_existing_target(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    skill = CodeSkill(Settings(dry_run=False))
    skill.handle(_cmd("scaffold python demoapp"))
    out = skill.handle(_cmd("scaffold python demoapp"))
    assert "already exists" in out


def test_unknown_language():
    out = CodeSkill(Settings(dry_run=True)).handle(_cmd("scaffold ruby thing"))
    assert "Supported languages" in out


def test_missing_name():
    out = CodeSkill(Settings(dry_run=True)).handle(_cmd("scaffold python"))
    assert "Name it" in out


def test_newproject_alias():
    out = CodeSkill(Settings(dry_run=True)).handle(_cmd("newproject thing"))
    assert "Python project 'thing'" in out
