"""End-to-end: a real Brain built from the bootstrap, parse -> route -> reply.

Uses the ``settings`` fixture (isolated DB, dry-run launchers, AI off) so
the whole pipeline is exercised without touching the network, a browser,
or the real home database.
"""

from __future__ import annotations

from core.brain import Brain


def test_help_lists_commands(settings):
    brain = Brain.create(settings)
    out = brain.process("help")
    assert "available commands" in out.text.lower()
    assert out.should_exit is False


def test_version(settings):
    brain = Brain.create(settings)
    out = brain.process("version")
    assert out.text.startswith("JARVIS ")
    assert out.should_exit is False


def test_empty_input_is_silent(settings):
    out = Brain.create(settings).process("   ")
    assert out.text == ""
    assert out.should_exit is False


def test_exit_signals_should_exit(settings):
    out = Brain.create(settings).process("exit")
    assert out.should_exit is True
    assert out.text == "Goodbye."


def test_remember_then_recall_roundtrip(settings):
    brain = Brain.create(settings)
    assert brain.process("remember buy milk").text == "Memory saved (#1)."
    assert "buy milk" in brain.process("recall").text


def test_time_command(settings):
    out = Brain.create(settings).process("time")
    assert "time" in out.text.lower()


def test_open_domain_is_dry_run(settings):
    out = Brain.create(settings).process("open github.com")
    assert out.text == "[dry-run] would open https://github.com"


def test_unknown_input_falls_back_to_ai(settings):
    # AI is off in the test settings, so the fallback explains how to enable it.
    out = Brain.create(settings).process("tell me a joke about cats")
    assert "isn't available" in out.text
    assert out.should_exit is False


# --- Phase 2 agents wired end-to-end through the Brain --------------------
def test_task_add_then_list(settings):
    brain = Brain.create(settings)
    assert brain.process("task buy milk").text.startswith("Task #")
    assert "buy milk" in brain.process("tasks").text


def test_pref_set_then_get(settings):
    brain = Brain.create(settings)
    brain.process("set name Tony")
    assert brain.process("get name").text == "Tony"


def test_files_ls_current_dir(settings):
    # Run from the project root, so main.py should be visible.
    out = Brain.create(settings).process("ls .")
    assert "main.py" in out.text


def test_research_unavailable_without_ai(settings):
    out = Brain.create(settings).process("research reinforcement learning")
    assert "isn't available" in out.text


def test_scaffold_dry_run(settings):
    # settings.dry_run is True, so nothing is written to disk.
    out = Brain.create(settings).process("scaffold python brand_new_demo")
    assert out.text.startswith("[dry-run] would create Python project")
