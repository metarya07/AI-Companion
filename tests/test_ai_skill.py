"""AISkill talks to a provider and degrades gracefully when one fails."""

from __future__ import annotations

from typing import List

from config.settings import Settings
from core.types import ParsedCommand
from skills.ai_skill import (
    AISkill,
    Message,
    NullProvider,
    OllamaProvider,
    OmniRouteProvider,
    OpenAIProvider,
    ProviderError,
    make_provider,
)


class FakeProvider:
    def __init__(self, reply: str = "hello from AI"):
        self.reply = reply
        self.calls: List[List[Message]] = []

    def chat(self, messages):
        self.calls.append(messages)
        return self.reply


def _settings() -> Settings:
    return Settings(ai_provider="none")  # provider is injected directly below


def _cmd(raw: str, verb: str, args: str) -> ParsedCommand:
    return ParsedCommand(raw=raw, verb=verb, args=args)


def test_explicit_ask_uses_args():
    provider = FakeProvider()
    skill = AISkill(provider, _settings())
    assert skill.handle(_cmd("ask explain decorators", "ask", "explain decorators")) == "hello from AI"
    # System prompt is prepended; the user's text is the args, not the verb.
    sent = provider.calls[0]
    assert sent[0]["role"] == "system"
    assert sent[-1] == {"role": "user", "content": "explain decorators"}


def test_unrecognised_input_uses_whole_sentence():
    provider = FakeProvider()
    skill = AISkill(provider, _settings())
    skill.handle(_cmd("who are you", "who", "are you"))
    # verb "who" is not a trigger, so the raw sentence is sent.
    assert provider.calls[0][-1]["content"] == "who are you"


def test_history_accumulates():
    provider = FakeProvider()
    skill = AISkill(provider, _settings())
    skill.handle(_cmd("ask hi", "ask", "hi"))
    assert skill.history == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello from AI"},
    ]


def test_empty_ask_prompts():
    skill = AISkill(FakeProvider(), _settings())
    assert "ask" in skill.handle(_cmd("ask", "ask", "")).lower()


def test_provider_error_is_handled_gracefully():
    skill = AISkill(NullProvider("ollama is offline"), _settings())
    out = skill.handle(_cmd("hello", "hello", ""))
    assert "isn't available" in out
    assert "ollama is offline" in out
    assert skill.history == []  # nothing recorded on failure


def test_make_provider_selects_by_setting():
    assert isinstance(make_provider(Settings(ai_provider="none")), NullProvider)
    assert isinstance(make_provider(Settings(ai_provider="ollama")), OllamaProvider)
    assert isinstance(make_provider(Settings(ai_provider="omniroute")), OmniRouteProvider)
    # OpenAI without a key falls back to NullProvider rather than crashing.
    assert isinstance(
        make_provider(Settings(ai_provider="openai", openai_api_key=None)), NullProvider
    )
    assert isinstance(
        make_provider(Settings(ai_provider="openai", openai_api_key="sk-test")),
        OpenAIProvider,
    )
