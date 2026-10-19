"""The Brain ties the pipeline together: parse -> route -> execute."""

from __future__ import annotations

from typing import Callable, Optional

from core.command_parser import CommandParser
from core.intent_router import IntentRouter
from core.skill_manager import SkillManager
from core.types import Response


class Brain:
    """Top-level orchestrator.

    Components are injected so the Brain is trivial to unit test with
    fakes. For normal use call :meth:`Brain.create`, which wires up the
    real skills via the bootstrap module.

    An optional ``recorder`` is called with ``(user_input, reply)`` after
    each non-empty turn; the bootstrap uses it to persist conversation
    history.
    """

    def __init__(
        self,
        parser: CommandParser,
        router: IntentRouter,
        manager: SkillManager,
        recorder: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.parser = parser
        self.router = router
        self.manager = manager
        self.recorder = recorder

    def process(self, user_input: str) -> Response:
        command = self.parser.parse(user_input)
        intent = self.router.route(command)
        text = self.manager.execute(intent, command)
        if self.recorder is not None and command.raw:
            try:
                self.recorder(command.raw, text)
            except Exception:  # noqa: BLE001 - logging must never break a turn
                pass
        return Response(text=text, should_exit=(intent == "exit"))

    @classmethod
    def create(cls, settings: Optional["object"] = None) -> "Brain":
        # Imported lazily to avoid a circular import (bootstrap imports Brain).
        from core.bootstrap import build_brain

        return build_brain(settings)
