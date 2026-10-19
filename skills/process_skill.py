"""Computer-control agent: inspect and close running processes.

Uses psutil (optional - degrades gracefully). Closing is name-based,
case-insensitive, refuses dangerously short queries, skips a small set of
critical OS processes and never targets JARVIS itself, and honours
``JARVIS_DRY_RUN`` so you can preview what would close.
"""

from __future__ import annotations

import os

from core.registry import Skill
from core.types import ParsedCommand

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

_TOP_N = 10
# Never terminate these, whatever the user types.
_PROTECTED = {
    "systemd", "init", "kernel", "launchd", "kthreadd",
    "wininit", "csrss", "services", "lsass", "smss", "winlogon",
    "system", "registry",
}


class ProcessSkill(Skill):
    name = "Processes"
    triggers = ("close", "kill", "processes", "top")
    help = (
        ("close <app>", "Close running processes matching a name"),
        ("processes", "List the top processes by memory use"),
    )

    def __init__(self, settings=None, ps=psutil) -> None:
        self.settings = settings
        self.ps = ps

    @property
    def _dry(self) -> bool:
        return bool(self.settings and getattr(self.settings, "dry_run", False))

    def handle(self, command: ParsedCommand) -> str:
        if self.ps is None:
            return "Process control needs psutil. Install it with: pip install psutil"
        verb, args = command.verb, command.args.strip()
        if verb in ("processes", "top"):
            return self._list()
        return self._close(args)

    # --- helpers -------------------------------------------------------------
    def _list(self) -> str:
        procs = []
        for proc in self.ps.process_iter(["pid", "name", "memory_info"]):
            info = proc.info
            mem = getattr(info.get("memory_info"), "rss", 0) or 0
            procs.append((mem, info.get("pid"), info.get("name") or "?"))
        procs.sort(reverse=True)
        lines = ["Top processes by memory:"]
        for mem, pid, name in procs[:_TOP_N]:
            lines.append(f"  {mem / (1024 ** 2):7.1f} MB  pid {pid}  {name}")
        return "\n".join(lines)

    def _close(self, name: str) -> str:
        query = name.strip().lower()
        if len(query) < 2:
            return "Please name the app to close, e.g. close chrome."

        own_pid = os.getpid()
        matches = []
        for proc in self.ps.process_iter(["pid", "name"]):
            pname = (proc.info.get("name") or "").lower()
            pid = proc.info.get("pid")
            if not pname or pid == own_pid:
                continue
            if pname in _PROTECTED or pname.replace(".exe", "") in _PROTECTED:
                continue
            if query in pname:
                matches.append(proc)

        if not matches:
            return f"No running process matches '{name}'."

        names = sorted({(p.info.get("name") or "?") for p in matches})
        if self._dry:
            return f"[dry-run] would close {len(matches)} process(es): {', '.join(names)}"

        closed = 0
        for proc in matches:
            try:
                proc.terminate()
                closed += 1
            except Exception:  # noqa: BLE001 - permission etc.
                pass
        if closed == 0:
            return f"Found {len(matches)} match(es) for '{name}' but couldn't close them (permissions?)."
        return f"Closed {closed} process(es) matching '{name}': {', '.join(names)}"
