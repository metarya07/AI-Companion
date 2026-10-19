"""Small value objects passed around the core pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedCommand:
    """A single line of user input, split into a verb and its arguments.

    ``verb`` is the lower-cased first word (the routing key) and ``args``
    is everything after it, untouched except for surrounding whitespace.
    ``raw`` is the original, stripped input - useful for the AI fallback,
    which wants the whole sentence rather than just the trailing words.
    """

    raw: str
    verb: str
    args: str

    @property
    def has_args(self) -> bool:
        return bool(self.args)


@dataclass(frozen=True)
class Response:
    """The result of processing one command.

    ``should_exit`` lets the REPL know it is time to stop without the
    fragile "print then re-check the raw string" dance the old loop used.
    """

    text: str
    should_exit: bool = False
