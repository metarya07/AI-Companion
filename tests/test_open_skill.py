"""OpenSkill decides between launching an app and opening a website."""

from __future__ import annotations

from config.settings import Settings
from core.types import ParsedCommand
from skills.app_skill import AppEntry, AppLauncher
from skills.open_skill import OpenSkill
from skills.web_skill import WebOpener


def _skill() -> OpenSkill:
    settings = Settings(dry_run=True)  # both launchers describe, never act
    catalog = {"firefox": AppEntry("Firefox", "firefox", "exec", exec_argv=["firefox"])}
    return OpenSkill(AppLauncher(settings, catalog=catalog), WebOpener(settings))


def _cmd(verb: str, args: str) -> ParsedCommand:
    return ParsedCommand(raw=f"{verb} {args}".strip(), verb=verb, args=args)


def test_installed_app_is_launched():
    out = _skill().handle(_cmd("open", "firefox"))
    assert out.startswith("[dry-run] would launch Firefox")


def test_explicit_domain_goes_to_browser():
    out = _skill().handle(_cmd("open", "github.com"))
    assert out == "[dry-run] would open https://github.com"


def test_alias_falls_back_to_website_when_no_app():
    # No "google" app in the catalog -> resolves to the website alias.
    out = _skill().handle(_cmd("open", "google"))
    assert out == "[dry-run] would open https://www.google.com"


def test_website_verb_forces_browser():
    out = _skill().handle(_cmd("website", "github"))
    assert out == "[dry-run] would open https://github.com"


def test_no_target_prompts():
    assert "Open what" in _skill().handle(_cmd("open", ""))


def test_unknown_target_explains():
    out = _skill().handle(_cmd("open", "totallyunknownthing"))
    assert "couldn't find" in out.lower()
