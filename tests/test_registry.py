"""SkillRegistry maps verbs to skills and tracks the fallback."""

from __future__ import annotations

import pytest

from core.registry import Skill, SkillRegistry
from core.types import ParsedCommand


class _Echo(Skill):
    name = "Echo"
    triggers = ("foo", "bar")

    def handle(self, command: ParsedCommand) -> str:
        return f"echo:{command.verb}"


class _Fallback(Skill):
    name = "Fallback"
    triggers = ("ask",)
    is_fallback = True

    def handle(self, command: ParsedCommand) -> str:
        return "fallback"


def test_register_exposes_verbs_and_skill_lookup():
    reg = SkillRegistry()
    skill = reg.register(_Echo())

    assert reg.get("foo") is skill
    assert reg.get("BAR") is skill  # lookup is case-insensitive
    assert reg.verbs() == {"foo", "bar"}
    assert skill in reg.skills()


def test_unknown_verb_returns_none():
    reg = SkillRegistry()
    reg.register(_Echo())
    assert reg.get("nope") is None


def test_duplicate_verb_raises():
    reg = SkillRegistry()
    reg.register(_Echo())
    with pytest.raises(ValueError):
        reg.register(_Echo())  # same triggers again


def test_fallback_is_tracked():
    reg = SkillRegistry()
    assert reg.fallback is None
    fb = reg.register(_Fallback())
    assert reg.fallback is fb
