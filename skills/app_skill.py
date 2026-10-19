"""Discovers and launches installed applications, cross-platform.

This replaces the original launcher, which walked ``C:\\Program Files``
looking for ``<name>.exe``. That approach hit two problems described in
the project notes:

* It descended into ``C:\\Program Files\\WindowsApps`` (Store apps), an
  ACL-locked folder, and trying to launch the stub raised
  ``PermissionError: [WinError 5] Access is denied``.
* Walking the whole of Program Files is slow.

The fix follows the notes' own conclusion - don't chase executables.
Instead each platform is discovered the reliable way:

* **Windows**: Start Menu ``.lnk`` / ``.url`` shortcuts (in ProgramData
  and the per-user AppData), launched with ``os.startfile`` - which also
  works for Store apps that the old method choked on.
* **macOS**: ``.app`` bundles under the Applications folders, launched
  with ``open``.
* **Linux**: ``.desktop`` entries under the XDG application directories,
  launched with ``gtk-launch`` / ``gio`` (with an ``Exec=`` fallback).

Names are matched fuzzily, so ``open chrome`` finds "Google Chrome".
Discovery is cached, and both discovery and launching can be injected for
testing (and a global dry-run mode describes actions instead of taking
them).
"""

from __future__ import annotations

import difflib
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


def _norm(name: str) -> str:
    """Normalise a name for matching: lower-case, alphanumerics only."""
    return "".join(ch for ch in name.lower() if ch.isalnum())


@dataclass
class AppEntry:
    display: str
    target: str
    kind: str  # "startfile" | "open" | "desktop" | "exec"
    desktop_file: Optional[str] = None
    exec_argv: Optional[List[str]] = None


# Built-in Windows commands that may not have Start Menu shortcuts.
_WINDOWS_BUILTINS = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "calc": ["calc.exe"],
    "cmd": ["cmd.exe"],
    "explorer": ["explorer.exe"],
    "paint": ["mspaint.exe"],
}


class AppLauncher:
    def __init__(
        self,
        settings=None,
        *,
        system: Optional[str] = None,
        catalog: Optional[Dict[str, AppEntry]] = None,
        launcher: Optional[Callable[[AppEntry], None]] = None,
    ) -> None:
        self.settings = settings
        self.system = (system or platform.system()).lower()
        self._catalog = catalog  # if provided, used verbatim (tests)
        self._launcher = launcher  # if provided, replaces real launching (tests)
        self._cache: Optional[Dict[str, AppEntry]] = None

    # --- public API ----------------------------------------------------------
    def open(self, name: str) -> Tuple[bool, Optional[str]]:
        """Try to launch ``name``.

        Returns ``(found, message)``. ``found`` is False when no matching
        application exists, letting the caller fall back to other handlers.
        """
        entry = self.find(name)
        if entry is None:
            return False, None

        if self.settings is not None and getattr(self.settings, "dry_run", False):
            return True, f"[dry-run] would launch {entry.display} ({entry.target})"

        try:
            self._launch(entry)
            return True, f"Opening {entry.display}\u2026"
        except PermissionError:
            return True, f"Couldn't open {entry.display}: permission denied."
        except FileNotFoundError:
            return True, f"Couldn't open {entry.display}: the launcher tool is missing."
        except Exception as exc:  # noqa: BLE001
            return True, f"Couldn't open {entry.display}: {exc}"

    def find(self, name: str) -> Optional[AppEntry]:
        catalog = self.catalog()
        key = _norm(name)
        if not key:
            return None
        if key in catalog:
            return catalog[key]
        for candidate, entry in catalog.items():
            if candidate.startswith(key):
                return entry
        for candidate, entry in catalog.items():
            if key in candidate:
                return entry
        close = difflib.get_close_matches(key, list(catalog), n=1, cutoff=0.8)
        return catalog[close[0]] if close else None

    def catalog(self, refresh: bool = False) -> Dict[str, AppEntry]:
        if self._catalog is not None:
            return self._catalog
        if self._cache is None or refresh:
            self._cache = self._discover()
        return self._cache

    # --- launching -----------------------------------------------------------
    def _launch(self, entry: AppEntry) -> None:
        if self._launcher is not None:
            self._launcher(entry)
            return
        if entry.kind == "startfile":
            os.startfile(entry.target)  # type: ignore[attr-defined]  # Windows only
        elif entry.kind == "open":
            subprocess.Popen(["open", entry.target])
        elif entry.kind == "desktop":
            self._launch_desktop(entry)
        elif entry.kind == "exec":
            subprocess.Popen(entry.exec_argv or [entry.target])
        else:  # pragma: no cover - defensive
            raise RuntimeError(f"Unknown launch kind: {entry.kind}")

    def _launch_desktop(self, entry: AppEntry) -> None:
        app_id = Path(entry.desktop_file).stem if entry.desktop_file else entry.target
        if shutil.which("gtk-launch"):
            subprocess.Popen(["gtk-launch", app_id])
            return
        if shutil.which("gio") and entry.desktop_file:
            subprocess.Popen(["gio", "launch", entry.desktop_file])
            return
        argv = entry.exec_argv
        if argv:
            subprocess.Popen(argv)
            return
        raise FileNotFoundError("install gtk-launch or gio to open desktop apps")

    # --- discovery -----------------------------------------------------------
    def _discover(self) -> Dict[str, AppEntry]:
        if self.system.startswith("win"):
            return self._discover_windows()
        if self.system == "darwin":
            return self._discover_macos()
        return self._discover_linux()

    @staticmethod
    def _add(catalog: Dict[str, AppEntry], display: str, entry: AppEntry) -> None:
        key = _norm(display)
        if key and key not in catalog:  # first writer wins, keeps it stable
            catalog[key] = entry

    def _discover_windows(self) -> Dict[str, AppEntry]:
        catalog: Dict[str, AppEntry] = {}
        dirs = [
            Path(os.environ.get("ProgramData", r"C:\ProgramData"))
            / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("APPDATA", ""))
            / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        ]
        for directory in dirs:
            if not directory.exists():
                continue
            try:
                shortcuts = list(directory.rglob("*"))
            except OSError:  # pragma: no cover - permission quirks
                continue
            for path in shortcuts:
                if path.suffix.lower() in (".lnk", ".url") and path.is_file():
                    self._add(catalog, path.stem, AppEntry(path.stem, str(path), "startfile"))
        for name, argv in _WINDOWS_BUILTINS.items():
            self._add(catalog, name, AppEntry(name, argv[0], "exec", exec_argv=argv))
        return catalog

    def _discover_macos(self) -> Dict[str, AppEntry]:
        catalog: Dict[str, AppEntry] = {}
        bases = ["/Applications", "/System/Applications", str(Path.home() / "Applications")]
        for base in bases:
            root = Path(base)
            if not root.exists():
                continue
            for pattern in ("*.app", "*/*.app"):  # include Utilities subfolder
                for app in root.glob(pattern):
                    self._add(catalog, app.stem, AppEntry(app.stem, str(app), "open"))
        return catalog

    def _discover_linux(self) -> Dict[str, AppEntry]:
        catalog: Dict[str, AppEntry] = {}
        dirs = [
            Path("/usr/share/applications"),
            Path("/usr/local/share/applications"),
            Path.home() / ".local" / "share" / "applications",
            Path("/var/lib/flatpak/exports/share/applications"),
            Path.home() / ".local" / "share" / "flatpak" / "exports" / "share" / "applications",
        ]
        for entry in os.environ.get("XDG_DATA_DIRS", "").split(":"):
            if entry:
                dirs.append(Path(entry) / "applications")

        seen = set()
        for directory in dirs:
            resolved = str(directory)
            if resolved in seen or not directory.exists():
                continue
            seen.add(resolved)
            for desktop in directory.glob("*.desktop"):
                name, exec_argv, usable = self._parse_desktop(desktop)
                if name and usable:
                    self._add(
                        catalog,
                        name,
                        AppEntry(name, desktop.stem, "desktop",
                                 desktop_file=str(desktop), exec_argv=exec_argv),
                    )
        return catalog

    @staticmethod
    def _parse_desktop(path: Path) -> Tuple[Optional[str], Optional[List[str]], bool]:
        name: Optional[str] = None
        exec_value: Optional[str] = None
        no_display = False
        is_application = True
        try:
            text = path.read_text(errors="ignore")
        except OSError:  # pragma: no cover
            return None, None, False
        in_main_section = False
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line.startswith("[") and line.endswith("]"):
                in_main_section = line == "[Desktop Entry]"
                continue
            if not in_main_section:
                continue
            if line.startswith("Name=") and name is None:
                name = line[len("Name="):].strip()
            elif line.startswith("Exec=") and exec_value is None:
                exec_value = line[len("Exec="):].strip()
            elif line.startswith("NoDisplay="):
                no_display = line.split("=", 1)[1].strip().lower() == "true"
            elif line.startswith("Type="):
                is_application = line.split("=", 1)[1].strip() == "Application"

        exec_argv = AppLauncher._clean_exec(exec_value) if exec_value else None
        usable = name is not None and not no_display and is_application
        return name, exec_argv, usable

    @staticmethod
    def _clean_exec(exec_value: str) -> List[str]:
        # Strip the desktop-entry field codes (%f, %u, %U, ...).
        tokens = [t for t in exec_value.split() if not (t.startswith("%") and len(t) == 2)]
        return tokens
