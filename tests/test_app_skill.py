"""AppLauncher: fuzzy name matching and safe, injected launching.

No real process is ever spawned: every test injects a catalog and a fake
launcher (or uses dry-run), so this runs identically on any OS.
"""

from __future__ import annotations

from config.settings import Settings
from skills.app_skill import AppEntry, AppLauncher


def _catalog():
    return {
        "googlechrome": AppEntry("Google Chrome", "chrome", "exec", exec_argv=["chrome"]),
        "firefox": AppEntry("Firefox", "firefox", "exec", exec_argv=["firefox"]),
        "spotify": AppEntry("Spotify", "spotify", "exec", exec_argv=["spotify"]),
    }


def test_exact_match():
    launcher = AppLauncher(catalog=_catalog())
    assert launcher.find("firefox").display == "Firefox"


def test_substring_match_finds_chrome():
    launcher = AppLauncher(catalog=_catalog())
    assert launcher.find("chrome").display == "Google Chrome"


def test_fuzzy_match_tolerates_a_typo():
    launcher = AppLauncher(catalog=_catalog())
    # "firefax" is close enough to "firefox" (>= 0.8 ratio).
    assert launcher.find("firefax").display == "Firefox"


def test_no_match_returns_none():
    launcher = AppLauncher(catalog=_catalog())
    assert launcher.find("zzzzz") is None


def test_open_invokes_launcher_and_reports():
    launched = []
    launcher = AppLauncher(catalog=_catalog(), launcher=launched.append)
    found, message = launcher.open("chrome")
    assert found is True
    assert "Google Chrome" in message
    assert launched and launched[0].display == "Google Chrome"


def test_open_unknown_lets_caller_fall_back():
    launcher = AppLauncher(catalog=_catalog(), launcher=lambda e: None)
    assert launcher.open("nonexistent") == (False, None)


def test_dry_run_describes_without_launching():
    launched = []
    settings = Settings(dry_run=True)
    launcher = AppLauncher(settings, catalog=_catalog(), launcher=launched.append)
    found, message = launcher.open("spotify")
    assert found is True
    assert message.startswith("[dry-run]")
    assert "Spotify" in message
    assert launched == []  # nothing actually launched


def test_parse_desktop_entry(tmp_path):
    path = tmp_path / "foo.desktop"
    path.write_text(
        "[Desktop Entry]\nName=Foo Bar\nExec=foobar %U\nType=Application\n"
    )
    name, argv, usable = AppLauncher._parse_desktop(path)
    assert name == "Foo Bar"
    assert argv == ["foobar"]  # the %U field code is stripped
    assert usable is True


def test_parse_desktop_skips_nodisplay(tmp_path):
    path = tmp_path / "hidden.desktop"
    path.write_text(
        "[Desktop Entry]\nName=Hidden\nExec=h\nType=Application\nNoDisplay=true\n"
    )
    _, _, usable = AppLauncher._parse_desktop(path)
    assert usable is False
