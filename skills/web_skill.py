"""Opens websites in the default browser (roadmap v0.5).

Handles three cases:

* friendly aliases (``open google`` -> https://www.google.com),
* bare domains (``open youtube.com``), and
* full URLs (``open https://example.org``).

Like the app launcher, the actual browser call is injectable and a
dry-run mode is supported, so opening a browser never happens during
tests or on a headless machine.
"""

from __future__ import annotations

import re
import webbrowser
from typing import Callable, Optional, Tuple

# A small, useful set of well-known sites. Extend freely.
ALIASES = {
    "google": "https://www.google.com",
    "github": "https://github.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "maps": "https://maps.google.com",
    "drive": "https://drive.google.com",
    "calendar": "https://calendar.google.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "wikipedia": "https://www.wikipedia.org",
    "stackoverflow": "https://stackoverflow.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "linkedin": "https://www.linkedin.com",
    "amazon": "https://www.amazon.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
}

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_WWW_RE = re.compile(r"^www\.", re.IGNORECASE)
_DOMAIN_RE = re.compile(r"^[\w-]+(\.[\w-]+)+(/.*)?$", re.IGNORECASE)


def _norm(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


class WebOpener:
    def __init__(
        self,
        settings=None,
        *,
        opener: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self.settings = settings
        self._opener = opener or webbrowser.open

    def is_explicit_url(self, target: str) -> bool:
        """True if ``target`` looks like a web address (not just an alias word)."""
        t = target.strip()
        return bool(_URL_RE.match(t) or _WWW_RE.match(t) or _DOMAIN_RE.match(t))

    def to_url(self, target: str) -> Optional[str]:
        """Resolve ``target`` to a URL, or None if it isn't web-openable."""
        t = target.strip()
        if not t:
            return None
        if _norm(t) in ALIASES:
            return ALIASES[_norm(t)]
        if _URL_RE.match(t):
            return t
        if _WWW_RE.match(t) or _DOMAIN_RE.match(t):
            return "https://" + t
        return None

    def open(self, target: str) -> Tuple[bool, Optional[str]]:
        url = self.to_url(target)
        if url is None:
            return False, None
        if self.settings is not None and getattr(self.settings, "dry_run", False):
            return True, f"[dry-run] would open {url}"
        try:
            self._opener(url)
            return True, f"Opening {url}"
        except Exception as exc:  # noqa: BLE001
            return True, f"Couldn't open the browser: {exc}"
