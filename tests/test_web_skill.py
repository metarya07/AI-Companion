"""WebOpener resolves aliases, domains and URLs without opening a browser."""

from __future__ import annotations

from config.settings import Settings
from skills.web_skill import WebOpener


def test_alias_resolves_to_known_url():
    web = WebOpener()
    assert web.to_url("google") == "https://www.google.com"
    assert web.to_url("github") == "https://github.com"


def test_bare_domain_gets_https():
    web = WebOpener()
    assert web.to_url("youtube.com") == "https://youtube.com"
    assert web.to_url("www.example.org") == "https://www.example.org"


def test_full_url_passes_through():
    web = WebOpener()
    assert web.to_url("https://example.org/page") == "https://example.org/page"


def test_plain_word_is_not_a_url():
    web = WebOpener()
    assert web.to_url("definitelynotadomain") is None


def test_is_explicit_url():
    web = WebOpener()
    assert web.is_explicit_url("github.com") is True
    assert web.is_explicit_url("https://a.b") is True
    assert web.is_explicit_url("www.a.b") is True
    assert web.is_explicit_url("chrome") is False  # alias word, not a URL


def test_open_calls_injected_opener():
    opened = []
    web = WebOpener(opener=lambda u: opened.append(u) or True)
    found, message = web.open("google")
    assert found is True
    assert "https://www.google.com" in message
    assert opened == ["https://www.google.com"]


def test_open_non_web_target_returns_false():
    web = WebOpener(opener=lambda u: True)
    assert web.open("notasite") == (False, None)


def test_dry_run_does_not_open():
    opened = []
    web = WebOpener(Settings(dry_run=True), opener=lambda u: opened.append(u) or True)
    found, message = web.open("github")
    assert found is True
    assert message.startswith("[dry-run]")
    assert "https://github.com" in message
    assert opened == []
