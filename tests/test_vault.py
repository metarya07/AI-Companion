"""Tests for VaultManager (Obsidian Markdown Vault operations)."""

import tempfile
from pathlib import Path

import pytest
from memory.vault import VaultManager, VaultNote


@pytest.fixture
def temp_vault(tmp_path: Path) -> VaultManager:
    vault_dir = tmp_path / "test_vault"
    return VaultManager(vault_dir)


def test_vault_init_creates_folders(temp_vault: VaultManager):
    assert temp_vault.vault_path.exists()
    assert (temp_vault.vault_path / ".obsidian").exists()
    assert (temp_vault.vault_path / ".obsidian" / "app.json").exists()
    assert (temp_vault.vault_path / "Daily").exists()
    assert (temp_vault.vault_path / "Ideas").exists()
    assert (temp_vault.vault_path / "Memories").exists()


def test_save_and_get_note(temp_vault: VaultManager):
    note = temp_vault.save_note(
        title="Neural Architecture",
        content="# Neural Architecture\n\nThis links to [[Synapse Config]].\n\n#brain #ai\n",
        folder="Ideas",
        tags=["neural"],
    )
    assert note.title == "Neural Architecture"
    assert note.folder == "Ideas"
    assert "brain" in note.tags
    assert "neural" in note.tags
    assert "Synapse Config" in note.links

    retrieved = temp_vault.get_note("Neural Architecture")
    assert retrieved is not None
    assert retrieved.title == "Neural Architecture"
    assert retrieved.word_count > 0


def test_list_and_search_notes(temp_vault: VaultManager):
    temp_vault.save_note(title="Quantum Physics", content="Study of quanta.", folder="Ideas")
    temp_vault.save_note(title="Groceries", content="Milk, eggs, coffee.", folder="Tasks")

    all_notes = temp_vault.list_notes()
    assert len(all_notes) >= 2

    ideas = temp_vault.list_notes(folder="Ideas")
    assert any(n.title == "Quantum Physics" for n in ideas)

    search_res = temp_vault.search_notes("coffee")
    assert len(search_res) == 1
    assert search_res[0].title == "Groceries"


def test_daily_note(temp_vault: VaultManager):
    daily = temp_vault.get_daily_note(create_if_missing=True)
    assert daily.folder == "Daily"
    assert "Daily Note" in daily.content

    # Retrieve again should match
    daily2 = temp_vault.get_daily_note()
    assert daily.abs_path == daily2.abs_path


def test_delete_note(temp_vault: VaultManager):
    temp_vault.save_note(title="Temp Note", content="Will be deleted.")
    assert temp_vault.get_note("Temp Note") is not None

    deleted = temp_vault.delete_note("Temp Note")
    assert deleted is True
    assert temp_vault.get_note("Temp Note") is None


def test_graph_data(temp_vault: VaultManager):
    temp_vault.save_note(
        title="Node A",
        content="Connecting to [[Node B]] and [[Node C]] #project",
    )
    temp_vault.save_note(
        title="Node B",
        content="Referencing [[Node A]] #project",
    )

    graph = temp_vault.get_graph_data()
    assert "nodes" in graph
    assert "edges" in graph

    node_ids = {n["id"] for n in graph["nodes"]}
    assert "ai-core" in node_ids
    assert "Node A" in node_ids
    assert "Node B" in node_ids
