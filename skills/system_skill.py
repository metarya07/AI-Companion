"""Reports system resource usage via psutil.

Two notable fixes:

* The old code called ``cpu_percent(interval=1)`` on every request, which
  blocked for a whole second each time (and twice for ``status``). Here the
  meter is primed once at start-up and then read with ``interval=None``,
  which returns instantly with the usage since the previous read.
* psutil is now optional: if it is not installed the skill explains how to
  get it instead of failing to import.
"""

from __future__ import annotations

import os
import time
from typing import Optional

from core.registry import Skill
from core.types import ParsedCommand

try:  # psutil is the one external dependency; degrade gracefully without it.
    import psutil
except ImportError:  # pragma: no cover - exercised only when psutil is absent
    psutil = None


def _gb(num_bytes: int) -> str:
    return f"{num_bytes / (1024 ** 3):.1f}"


def _root_path() -> str:
    # "/" on POSIX, "C:\\" on Windows.
    return os.path.abspath(os.sep)


class SystemSkill(Skill):
    name = "System"
    triggers = ("cpu", "ram", "disk", "battery", "uptime", "status")
    help = (
        ("cpu", "Current CPU usage"),
        ("ram", "Current RAM usage"),
        ("disk", "Disk usage of the system drive"),
        ("battery", "Battery level (laptops)"),
        ("uptime", "How long the machine has been on"),
        ("status", "A full system snapshot"),
    )

    def __init__(self, ps=psutil) -> None:
        self.ps = ps
        if self.ps is not None:
            try:
                # Prime the CPU meter so later reads are instant and accurate.
                self.ps.cpu_percent(interval=None)
            except Exception:  # pragma: no cover - defensive
                pass

    def handle(self, command: ParsedCommand) -> str:
        if self.ps is None:
            return "System monitoring needs psutil. Install it with: pip install psutil"

        verb = command.verb
        if verb == "cpu":
            return self._cpu()
        if verb == "ram":
            return self._ram()
        if verb == "disk":
            return self._disk()
        if verb == "battery":
            return self._battery()
        if verb == "uptime":
            return self._uptime()
        if verb == "status":
            return self._status()
        return "I don't understand that system command."

    # --- individual readings -------------------------------------------------
    def _cpu(self) -> str:
        return f"CPU usage: {self.ps.cpu_percent(interval=None):.1f}%"

    def _ram(self) -> str:
        mem = self.ps.virtual_memory()
        return f"RAM usage: {mem.percent:.1f}% ({_gb(mem.used)} / {_gb(mem.total)} GB)"

    def _disk(self) -> str:
        disk = self.ps.disk_usage(_root_path())
        return f"Disk usage: {disk.percent:.1f}% ({_gb(disk.used)} / {_gb(disk.total)} GB)"

    def _battery(self) -> str:
        battery = self._read_battery()
        if battery is None:
            return "No battery detected (or this machine isn't a laptop)."
        plugged = " (charging)" if getattr(battery, "power_plugged", False) else ""
        return f"Battery: {battery.percent:.0f}%{plugged}"

    def _uptime(self) -> str:
        seconds = int(time.time() - self.ps.boot_time())
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours or days:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return "Uptime: " + " ".join(parts)

    def _status(self) -> str:
        lines = [self._cpu(), self._ram(), self._disk()]
        if self._read_battery() is not None:
            lines.append(self._battery())
        lines.append(self._uptime())
        return "\n".join(lines)

    def _read_battery(self) -> Optional[object]:
        getter = getattr(self.ps, "sensors_battery", None)
        if getter is None:
            return None
        try:
            return getter()
        except Exception:  # pragma: no cover - platform dependent
            return None
