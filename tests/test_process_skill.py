"""ProcessSkill: listing and closing via an injected fake psutil."""

from __future__ import annotations

from types import SimpleNamespace

from config.settings import Settings
from core.types import ParsedCommand
from skills.process_skill import ProcessSkill


class FakeProc:
    def __init__(self, pid, name, rss=0):
        self.info = {"pid": pid, "name": name, "memory_info": SimpleNamespace(rss=rss)}
        self.terminated = False

    def terminate(self):
        self.terminated = True


class FakePsutil:
    def __init__(self, procs):
        self._procs = procs

    def process_iter(self, attrs=None):
        return list(self._procs)


def _cmd(verb: str, args: str = "") -> ParsedCommand:
    return ParsedCommand(raw=f"{verb} {args}".strip(), verb=verb, args=args)


def test_close_terminates_matching():
    chrome = FakeProc(111, "chrome", rss=200)
    firefox = FakeProc(222, "firefox", rss=100)
    skill = ProcessSkill(ps=FakePsutil([chrome, firefox]))
    out = skill.handle(_cmd("close", "chrome"))
    assert "Closed 1" in out and "chrome" in out
    assert chrome.terminated is True
    assert firefox.terminated is False


def test_close_short_query_refused():
    skill = ProcessSkill(ps=FakePsutil([FakeProc(1, "x")]))
    assert "name the app" in skill.handle(_cmd("close", "x"))


def test_close_no_match():
    skill = ProcessSkill(ps=FakePsutil([FakeProc(1, "chrome")]))
    assert "No running process matches" in skill.handle(_cmd("close", "zzz"))


def test_close_skips_protected():
    systemd = FakeProc(1, "systemd")
    skill = ProcessSkill(ps=FakePsutil([systemd]))
    assert "No running process matches" in skill.handle(_cmd("close", "systemd"))
    assert systemd.terminated is False


def test_dry_run_previews_without_closing():
    firefox = FakeProc(222, "firefox")
    skill = ProcessSkill(Settings(dry_run=True), ps=FakePsutil([firefox]))
    out = skill.handle(_cmd("close", "firefox"))
    assert out.startswith("[dry-run]") and "firefox" in out
    assert firefox.terminated is False


def test_processes_lists_by_memory():
    procs = [FakeProc(1, "small", rss=10), FakeProc(2, "big", rss=9999)]
    out = ProcessSkill(ps=FakePsutil(procs)).handle(_cmd("processes"))
    assert "Top processes by memory" in out
    # The bigger process should be listed before the smaller one.
    assert out.index("big") < out.index("small")


def test_missing_psutil_message():
    skill = ProcessSkill(ps=None)
    assert "needs psutil" in skill.handle(_cmd("processes"))
