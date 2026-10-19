"""CommandParser splits raw input into verb + args exactly once."""

from __future__ import annotations

from core.command_parser import CommandParser


def test_empty_input_yields_empty_command():
    cmd = CommandParser().parse("")
    assert cmd.raw == ""
    assert cmd.verb == ""
    assert cmd.args == ""
    assert cmd.has_args is False


def test_whitespace_only_is_treated_as_empty():
    cmd = CommandParser().parse("    \t  ")
    assert cmd.verb == ""
    assert cmd.args == ""


def test_single_word_has_verb_but_no_args():
    cmd = CommandParser().parse("time")
    assert cmd.verb == "time"
    assert cmd.args == ""
    assert cmd.has_args is False


def test_verb_is_lowercased_and_args_preserved():
    cmd = CommandParser().parse("Remember Buy Milk")
    assert cmd.verb == "remember"
    assert cmd.args == "Buy Milk"
    assert cmd.has_args is True
    # raw keeps the original casing for the AI fallback.
    assert cmd.raw == "Remember Buy Milk"


def test_surrounding_whitespace_is_stripped():
    cmd = CommandParser().parse("   forget   7   ")
    assert cmd.verb == "forget"
    assert cmd.args == "7"


def test_none_input_is_safe():
    cmd = CommandParser().parse(None)  # type: ignore[arg-type]
    assert cmd.verb == ""
