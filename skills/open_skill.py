"""The ``open`` command - resolves apps vs. websites.

The project notes use ``open`` for both apps (``open chrome``) and sites
(``open youtube.com``). This skill resolves the ambiguity:

1. ``website``/``site``/``goto`` always mean the browser.
2. A target that looks like a URL or domain goes to the browser.
3. Otherwise try to launch an installed app.
4. If no app matches, fall back to a known website alias.

So ``open chrome`` launches the browser app, ``open youtube.com`` opens
the site, and ``open google`` opens the site when no Google app exists.
"""

from __future__ import annotations

from core.registry import Skill
from core.types import ParsedCommand
from skills.app_skill import AppLauncher
from skills.web_skill import WebOpener

_WEB_ONLY_VERBS = {"website", "site", "goto"}


class OpenSkill(Skill):
    name = "Launcher"
    triggers = ("open", "launch", "run", "start", "website", "site", "goto")
    help = (
        ("open <app>", "Launch an installed application (open chrome)"),
        ("open <site>", "Open a website (open google, open youtube.com)"),
    )

    def __init__(self, apps: AppLauncher, web: WebOpener) -> None:
        self.apps = apps
        self.web = web

    def handle(self, command: ParsedCommand) -> str:
        target = command.args.strip()
        if not target:
            return "Open what? Try: open chrome   or   open github.com"

        # 1. Explicit website request.
        if command.verb in _WEB_ONLY_VERBS:
            found, message = self.web.open(target)
            return message if found else f"I couldn't open '{target}' as a website."

        # 2. Looks like a URL/domain -> browser.
        if self.web.is_explicit_url(target):
            found, message = self.web.open(target)
            if found:
                return message

        # 3. Installed application.
        found, message = self.apps.open(target)
        if found:
            return message

        # 4. Fall back to a known website alias.
        found, message = self.web.open(target)
        if found:
            return message

        return (
            f"I couldn't find an app or website called '{target}'. "
            "Try the full name, or 'open <something>.com' for a website."
        )
