"""ResearchSkill: AI-backed, with graceful failure when unavailable."""

from __future__ import annotations

from config.settings import Settings
from core.types import ParsedCommand
from skills.ai_skill import NullProvider, ProviderError
from skills.research_skill import ResearchSkill


class FakeProvider:
    def __init__(self):
        self.last_messages = None

    def chat(self, messages):
        self.last_messages = messages
        return "BRIEFING"


class BoomProvider:
    def chat(self, messages):
        raise ProviderError("model exploded")


def _cmd(raw: str) -> ParsedCommand:
    parts = raw.split(maxsplit=1)
    verb = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    return ParsedCommand(raw=raw, verb=verb, args=args)


def test_research_calls_provider():
    provider = FakeProvider()
    skill = ResearchSkill(provider, Settings())
    assert skill.handle(_cmd("research transformers")) == "BRIEFING"
    roles = [m["role"] for m in provider.last_messages]
    assert roles == ["system", "user"]
    assert "transformers" in provider.last_messages[1]["content"]


def test_compare_and_summarize():
    provider = FakeProvider()
    skill = ResearchSkill(provider, Settings())
    assert skill.handle(_cmd("compare python vs go")) == "BRIEFING"
    assert "Compare" in provider.last_messages[1]["content"]
    assert skill.handle(_cmd("summarize some long text here")) == "BRIEFING"


def test_empty_args_prompts():
    skill = ResearchSkill(FakeProvider(), Settings())
    assert "Research what" in skill.handle(_cmd("research"))


def test_graceful_when_provider_unavailable():
    skill = ResearchSkill(NullProvider("ollama not running"), Settings())
    out = skill.handle(_cmd("research anything"))
    assert "isn't available" in out
    assert "ollama not running" in out


def test_provider_error_is_handled():
    skill = ResearchSkill(BoomProvider(), Settings())
    out = skill.handle(_cmd("research anything"))
    assert "isn't available" in out and "model exploded" in out
