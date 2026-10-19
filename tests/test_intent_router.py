"""IntentRouter turns a parsed command into an intent string."""

from __future__ import annotations

import pytest

from core.command_parser import CommandParser
from core.intent_router import IntentRouter
from core.registry import Skill, SkillRegistry
from core.types import ParsedCommand


class _Known(Skill):
    name = "Known"
    triggers = ("time", "cpu")

    def handle(self, command: ParsedCommand) -> str:  # pragma: no cover
        return "ok"


@pytest.fixture
def router() -> IntentRouter:
    reg = SkillRegistry()
    reg.register(_Known())
    return IntentRouter(reg)


def _route(router: IntentRouter, text: str) -> str:
    return router.route(CommandParser().parse(text))


def test_empty_input_routes_to_empty(router):
    assert _route(router, "") == "empty"


@pytest.mark.parametrize("word", ["exit", "quit", "bye", "EXIT"])
def test_exit_words_route_to_exit(router, word):
    assert _route(router, word) == "exit"


@pytest.mark.parametrize("word", ["help", "version"])
def test_meta_words_pass_through(router, word):
    assert _route(router, word) == word


def test_known_verb_routes_to_itself(router):
    assert _route(router, "time now") == "time"
    assert _route(router, "cpu") == "cpu"


def test_unknown_verb_routes_to_chat(router):
    assert _route(router, "what is a monad") == "chat"
