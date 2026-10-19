"""The skill plugin layer.

The original design hard-wired every command into both
``IntentRouter`` and ``SkillManager``: adding a skill meant editing two
files and keeping a help string in sync by hand. Here, each skill simply
declares the verbs it answers to and a few help lines, then registers
itself. The router and manager read from the registry, so nothing else
needs to change when a new skill is added.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from core.types import ParsedCommand

# A help entry is a (command, description) pair, e.g. ("time", "Show the time").
HelpEntry = Tuple[str, str]


class Skill:
    """Base class for every skill.

    Subclasses set :attr:`name`, :attr:`triggers` and :attr:`help`, and
    implement :meth:`handle`. A skill marked with ``is_fallback = True``
    receives any input that no other skill claims (used by the AI skill).
    """

    name: str = "skill"
    triggers: Sequence[str] = ()
    help: Sequence[HelpEntry] = ()
    is_fallback: bool = False

    def handle(self, command: ParsedCommand) -> str:  # pragma: no cover - abstract
        raise NotImplementedError


class SkillRegistry:
    """Holds the registered skills and maps verbs to the skill that owns them."""

    def __init__(self) -> None:
        self._by_verb: Dict[str, Skill] = {}
        self._skills: List[Skill] = []
        self.fallback: Optional[Skill] = None

    def register(self, skill: Skill) -> Skill:
        """Register ``skill`` and return it (so registration reads nicely)."""
        self._skills.append(skill)
        for trigger in skill.triggers:
            verb = trigger.lower()
            if verb in self._by_verb:
                raise ValueError(
                    f"Verb {verb!r} is already handled by "
                    f"{self._by_verb[verb].name!r}; {skill.name!r} cannot reuse it."
                )
            self._by_verb[verb] = skill
        if skill.is_fallback:
            self.fallback = skill
        return skill

    def get(self, verb: str) -> Optional[Skill]:
        return self._by_verb.get(verb.lower())

    def verbs(self) -> set:
        return set(self._by_verb)

    def skills(self) -> List[Skill]:
        return list(self._skills)
