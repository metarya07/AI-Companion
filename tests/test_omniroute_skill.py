"""Tests for OmniRouteSkill and OmniRouteProvider."""

from __future__ import annotations

from config.settings import Settings
from core.types import ParsedCommand
from skills.ai_skill import OmniRouteProvider, ProviderError
from skills.omniroute_skill import OmniRouteSkill


def _cmd(raw: str, verb: str, args: str) -> ParsedCommand:
    return ParsedCommand(raw=raw, verb=verb, args=args)


def test_dry_run_start():
    settings = Settings(dry_run=True)
    skill = OmniRouteSkill(settings)
    out = skill.handle(_cmd("omniroute start", "omniroute", "start"))
    assert "DRY RUN" in out or "already running" in out


def test_dry_run_sync():
    settings = Settings(dry_run=True)
    skill = OmniRouteSkill(settings)
    out = skill.handle(_cmd("omniroute sync", "omniroute", "sync"))
    assert "DRY RUN" in out
    assert "omniroute setup-claude" in out


def test_dry_run_web():
    settings = Settings(dry_run=True)
    skill = OmniRouteSkill(settings)
    out = skill.handle(_cmd("omniroute web", "omniroute", "web"))
    assert "DRY RUN" in out
    assert "42100" in out


def test_dry_run_claude():
    settings = Settings(dry_run=True)
    skill = OmniRouteSkill(settings)
    out = skill.handle(_cmd("claude auto-best-free", "claude", "auto-best-free"))
    assert "DRY RUN" in out
    assert "auto-best-free" in out


def test_unknown_subcommand():
    settings = Settings(dry_run=True)
    skill = OmniRouteSkill(settings)
    out = skill.handle(_cmd("omniroute foobar", "omniroute", "foobar"))
    assert "Unknown omniroute action" in out


def test_omniroute_status():
    settings = Settings()
    skill = OmniRouteSkill(settings)
    out = skill.handle(_cmd("omniroute status", "omniroute", "status"))
    assert "OmniRoute Status:" in out


def test_omniroute_provider_offline_error():
    provider = OmniRouteProvider(
        host="http://127.0.0.1:1",  # guaranteed offline port
        model="auto-best-free",
        timeout=0.1,
    )
    try:
        provider.chat([{"role": "user", "content": "hi"}])
        assert False, "Should have raised ProviderError"
    except ProviderError as exc:
        assert "can't reach OmniRoute" in str(exc)
