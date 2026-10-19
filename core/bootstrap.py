"""Wires the real skills together and builds a ready-to-use Brain.

Adding a new skill is a one-line change here (plus the skill file) - the
router and manager pick it up automatically from the registry.
"""

from __future__ import annotations

from typing import Optional

from config.settings import Settings
from core import __version__
from core.brain import Brain
from core.command_parser import CommandParser
from core.intent_router import IntentRouter
from core.registry import SkillRegistry
from core.skill_manager import SkillManager
from memory.database import Database
from memory.history import HistoryStore
from memory.prefs import PrefStore
from memory.tasks import TaskStore
from memory.vault import VaultManager
from skills.ai_skill import AISkill, make_provider
from skills.app_skill import AppLauncher
from skills.code_skill import CodeSkill
from skills.files_skill import FilesSkill
from skills.history_skill import HistorySkill
from skills.memory_skill import MemorySkill
from skills.obsidian_skill import ObsidianSkill
from skills.omniroute_skill import OmniRouteSkill
from skills.open_skill import OpenSkill
from skills.prefs_skill import PrefSkill
from skills.process_skill import ProcessSkill
from skills.research_skill import ResearchSkill
from skills.schedule_skill import ScheduleSkill
from skills.system_skill import SystemSkill
from skills.task_skill import TaskSkill
from skills.time_skill import TimeSkill
from skills.vision_skill import VisionSkill
from skills.web_skill import WebOpener
from memory.schedules import ScheduleStore


def build_registry(settings: Settings) -> SkillRegistry:
    registry = SkillRegistry()
    db_path = settings.db_path
    vault = VaultManager(settings.vault_path)

    # --- memory agent --------------------------------------------------------
    registry.register(MemorySkill(Database(db_path)))
    registry.register(ObsidianSkill(vault))
    registry.register(PrefSkill(PrefStore(db_path)))
    registry.register(HistorySkill(HistoryStore(db_path)))

    # --- everyday utilities --------------------------------------------------
    registry.register(TimeSkill())
    registry.register(SystemSkill())
    registry.register(ProcessSkill(settings))

    # --- computer control ----------------------------------------------------
    registry.register(OpenSkill(AppLauncher(settings), WebOpener(settings)))
    registry.register(FilesSkill(settings))

    # --- planning + automation ----------------------------------------------
    registry.register(TaskSkill(TaskStore(db_path)))
    registry.register(ScheduleSkill(ScheduleStore(db_path)))

    # --- coding + research (AI-backed) --------------------------------------
    registry.register(CodeSkill(settings))
    registry.register(ResearchSkill(make_provider(settings), settings))
    registry.register(OmniRouteSkill(settings))

    # --- vision --------------------------------------------------------------
    registry.register(VisionSkill(settings))

    # The AI skill is the fallback for unrecognised input.
    registry.register(AISkill(make_provider(settings), settings))
    return registry


def build_brain(settings: Optional[Settings] = None) -> Brain:
    settings = settings or Settings.from_env()
    registry = build_registry(settings)
    router = IntentRouter(registry)
    manager = SkillManager(registry, fallback=registry.fallback, version=__version__)
    # Persist every turn to the conversation log (same DB file).
    recorder = HistoryStore(settings.db_path).add
    return Brain(CommandParser(), router, manager, recorder=recorder)
