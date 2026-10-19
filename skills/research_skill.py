"""Research agent: briefings, comparisons and summaries via the AI model.

This uses the configured AI provider (the same local Ollama / OpenAI
setup as the chat skill) and therefore relies on the model's own
knowledge - it does not yet fetch live web pages (that's a future step),
so it states that limitation honestly. When no provider is reachable it
explains how to enable one instead of failing.

Examples:
    research reinforcement learning
    compare PostgreSQL vs MySQL
    summarize <paste some text>
"""

from __future__ import annotations

from skills.ai_skill import ChatProvider, ProviderError
from core.registry import Skill
from core.types import ParsedCommand

_SYSTEM = (
    "You are JARVIS's research assistant. Produce clear, well-structured, "
    "factual answers. Note uncertainty rather than inventing specifics."
)


class ResearchSkill(Skill):
    name = "Researcher"
    triggers = ("research", "compare", "summarize")
    help = (
        ("research <topic>", "A structured briefing on a topic"),
        ("compare <a> vs <b>", "Compare two things"),
        ("summarize <text>", "Summarise some text"),
    )

    def __init__(self, provider: ChatProvider, settings) -> None:
        self.provider = provider
        self.settings = settings

    def handle(self, command: ParsedCommand) -> str:
        verb, args = command.verb, command.args.strip()
        if not args:
            return {
                "research": "Research what? e.g. research transformer models",
                "compare": "Compare what? e.g. compare Python vs Go",
                "summarize": "Summarise what? Paste the text after 'summarize'.",
            }[verb]

        prompt = self._prompt(verb, args)
        try:
            return self.provider.chat(
                [{"role": "system", "content": _SYSTEM},
                 {"role": "user", "content": prompt}]
            )
        except ProviderError as exc:
            return self._unavailable(str(exc))
        except Exception as exc:  # noqa: BLE001
            return self._unavailable(f"{type(exc).__name__}: {exc}")

    @staticmethod
    def _prompt(verb: str, args: str) -> str:
        if verb == "research":
            return (
                f"Give a concise briefing on: {args}.\n"
                "Cover: what it is, why it matters, the key points, and a "
                "one-line summary. Use short sections."
            )
        if verb == "compare":
            return (
                f"Compare the following, point by point, then give a short "
                f"recommendation on when to choose each: {args}."
            )
        return f"Summarise the following clearly and briefly:\n\n{args}"

    def _unavailable(self, reason: str) -> str:
        return (
            "The research assistant needs the AI model, which isn't available "
            "right now.\n"
            f"Reason: {reason}\n"
            "Enable a local model with Ollama (https://ollama.com) or set "
            "OPENAI_API_KEY and JARVIS_AI_PROVIDER=openai."
        )
