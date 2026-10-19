"""SystemSkill formats psutil readings; a fake psutil keeps it fast.

The fake avoids the real ``cpu_percent`` blocking sample and lets us
assert on exact formatting deterministically.
"""

from __future__ import annotations

import time
from types import SimpleNamespace

from skills.system_skill import SystemSkill
from core.types import ParsedCommand


class FakePsutil:
    def __init__(self, with_battery: bool = True):
        self._with_battery = with_battery

    def cpu_percent(self, interval=None):
        return 12.0

    def virtual_memory(self):
        return SimpleNamespace(percent=50.0, used=8 * 1024 ** 3, total=16 * 1024 ** 3)

    def disk_usage(self, path):
        return SimpleNamespace(percent=40.0, used=200 * 1024 ** 3, total=500 * 1024 ** 3)

    def boot_time(self):
        return time.time() - 3700  # ~1h 1m ago

    def sensors_battery(self):
        if not self._with_battery:
            return None
        return SimpleNamespace(percent=88.0, power_plugged=True)


def _cmd(verb: str) -> ParsedCommand:
    return ParsedCommand(raw=verb, verb=verb, args="")


def test_cpu_formats_percentage():
    skill = SystemSkill(ps=FakePsutil())
    assert skill.handle(_cmd("cpu")) == "CPU usage: 12.0%"


def test_ram_shows_percent_and_gb():
    skill = SystemSkill(ps=FakePsutil())
    assert skill.handle(_cmd("ram")) == "RAM usage: 50.0% (8.0 / 16.0 GB)"


def test_disk_shows_percent_and_gb():
    skill = SystemSkill(ps=FakePsutil())
    assert skill.handle(_cmd("disk")) == "Disk usage: 40.0% (200.0 / 500.0 GB)"


def test_battery_reports_charging():
    skill = SystemSkill(ps=FakePsutil())
    assert skill.handle(_cmd("battery")) == "Battery: 88% (charging)"


def test_battery_absent_message():
    skill = SystemSkill(ps=FakePsutil(with_battery=False))
    assert "No battery" in skill.handle(_cmd("battery"))


def test_uptime_starts_with_label():
    skill = SystemSkill(ps=FakePsutil())
    assert skill.handle(_cmd("uptime")).startswith("Uptime:")


def test_status_bundles_readings():
    out = SystemSkill(ps=FakePsutil()).handle(_cmd("status"))
    assert "CPU usage" in out
    assert "RAM usage" in out
    assert "Disk usage" in out


def test_missing_psutil_is_graceful():
    skill = SystemSkill(ps=None)
    assert "psutil" in skill.handle(_cmd("cpu"))
