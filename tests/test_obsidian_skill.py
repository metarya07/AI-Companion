"""Tests for ObsidianSkill."""

from pathlib import Path
import pytest
from core.command_parser import CommandParser
from memory.vault import VaultManager
from skills.obsidian_skill import ObsidianSkill


@pytest.fixture
def temp_vault(tmp_path: Path) -> VaultManager:
    return VaultManager(tmp_path / "obsidian_vault")


@pytest.fixture
def obsidian_skill(temp_vault: VaultManager) -> ObsidianSkill:
    return ObsidianSkill(temp_vault)


def test_obsidian_skill_note_command(obsidian_skill: ObsidianSkill, temp_vault: VaultManager):
    parser = CommandParser()
    cmd = parser.parse("note Project Quantum: Explore superposition #quantum")
    response = obsidian_skill.handle(cmd)

    assert "Saved note" in response
    assert "Project Quantum" in response
    note = temp_vault.get_note("Project Quantum")
    assert note is not None
    assert "Explore superposition" in note.content


def test_obsidian_skill_daily_command(obsidian_skill: ObsidianSkill, temp_vault: VaultManager):
    parser = CommandParser()
    cmd = parser.parse("daily Completed chapter 1 of textbook")
    response = obsidian_skill.handle(cmd)

    assert "Appended to daily note" in response
    daily = temp_vault.get_daily_note()
    assert "Completed chapter 1 of textbook" in daily.content


def test_obsidian_skill_vault_list_and_search(obsidian_skill: ObsidianSkill, temp_vault: VaultManager):
    temp_vault.save_note("Cosmology", "Study of the universe.")
    parser = CommandParser()

    list_cmd = parser.parse("vault list")
    list_resp = obsidian_skill.handle(list_cmd)
    assert "Cosmology" in list_resp

    search_cmd = parser.parse("vault search universe")
    search_resp = obsidian_skill.handle(search_cmd)
    assert "Cosmology" in search_resp


def test_obsidian_skill_open(obsidian_skill: ObsidianSkill):
    parser = CommandParser()
    cmd = parser.parse("vault open")
    resp = obsidian_skill.handle(cmd)
    assert "Vault" in resp or "Opened" in resp
