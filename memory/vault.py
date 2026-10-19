"""Obsidian Markdown Vault Manager for JARVIS.

Manages notes, folders, wikilinks, tags, daily notes, and graph topological
data inside a standard local Obsidian Vault directory.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

WIKILINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
TAG_PATTERN = re.compile(r"(?:^|\s)#([a-zA-Z0-9_\-\/]+)")


@dataclass
class VaultNote:
    """Representation of an Obsidian Markdown Note."""

    title: str
    rel_path: str
    abs_path: str
    content: str
    tags: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    folder: str = ""
    modified_at: float = 0.0

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @property
    def char_count(self) -> int:
        return len(self.content)


class VaultManager:
    """Manages reading, writing, searching and graph generation in an Obsidian Vault."""

    DEFAULT_FOLDERS = ["Daily", "Ideas", "Memories", "Tasks", "AI-Conversations"]

    def __init__(self, vault_path: Union[str, Path]) -> None:
        self.vault_path = Path(vault_path).resolve()
        self._init_vault()

    def _init_vault(self) -> None:
        """Ensure vault folder structure and standard Obsidian configuration exist."""
        self.vault_path.mkdir(parents=True, exist_ok=True)
        for folder in self.DEFAULT_FOLDERS:
            (self.vault_path / folder).mkdir(parents=True, exist_ok=True)

        obsidian_dir = self.vault_path / ".obsidian"
        obsidian_dir.mkdir(parents=True, exist_ok=True)

        app_json = obsidian_dir / "app.json"
        if not app_json.exists():
            app_config = {
                "attachmentFolderPath": "Attachments",
                "alwaysUpdateLinks": True,
                "useMarkdownLinks": False,
            }
            app_json.write_text(json.dumps(app_config, indent=2), encoding="utf-8")

        # Seed an introduction note if vault is completely empty
        intro_note = self.vault_path / "Ideas" / "JARVIS Neural Knowledge Vault.md"
        if not intro_note.exists() and len(list(self.vault_path.glob("**/*.md"))) == 0:
            intro_content = (
                "# ⬡ JARVIS Neural Knowledge Vault\n\n"
                "Welcome to your local **Obsidian Knowledge Base**, integrated with JARVIS AI.\n\n"
                "## Features\n"
                "- 📝 **Markdown Notes**: Edit and store knowledge nodes in standard Markdown.\n"
                "- 🧠 **Neural Graph**: Visualize note relationships and `[[wikilinks]]`.\n"
                "- 🤖 **AI Connected**: OmniRoute AI can read and write directly to this vault.\n"
                "- 🏷️ **Tags**: Categorize notes using `#knowledge`, `#jarvis`, `#ideas`.\n\n"
                "## Quick Links\n"
                "- [[Daily Tasks]]\n"
                "- [[AI Operating Principles]]\n\n"
                "#jarvis #neural #knowledge\n"
            )
            intro_note.write_text(intro_content, encoding="utf-8")

            # Seed a sample tasks note
            tasks_note = self.vault_path / "Tasks" / "Daily Tasks.md"
            tasks_content = (
                "# Daily Tasks & Action Items\n\n"
                "- [ ] Review neural network graphs\n"
                "- [ ] Test OmniRoute multi-model switching\n"
                "- [x] Initialize Obsidian vault integration\n\n"
                "#tasks #action\n"
            )
            tasks_note.write_text(tasks_content, encoding="utf-8")

    def _parse_note_content(self, content: str, rel_path: str, abs_path: Path) -> VaultNote:
        title = abs_path.stem
        # Parse links [[...]]
        links = [match.strip() for match in WIKILINK_PATTERN.findall(content)]
        # Parse tags #...
        tags = [match.strip() for match in TAG_PATTERN.findall(content)]

        folder = str(Path(rel_path).parent)
        if folder == ".":
            folder = ""

        mod_time = abs_path.stat().st_mtime if abs_path.exists() else 0.0

        return VaultNote(
            title=title,
            rel_path=rel_path.replace("\\", "/"),
            abs_path=str(abs_path),
            content=content,
            tags=sorted(list(set(tags))),
            links=sorted(list(set(links))),
            folder=folder.replace("\\", "/"),
            modified_at=mod_time,
        )

    def list_notes(self, folder: Optional[str] = None) -> List[VaultNote]:
        """List all notes in vault, optionally filtering by folder."""
        notes: List[VaultNote] = []
        base_dir = self.vault_path if not folder else (self.vault_path / folder)
        if not base_dir.exists():
            return []

        for p in base_dir.rglob("*.md"):
            if ".obsidian" in p.parts:
                continue
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                rel_path = str(p.relative_to(self.vault_path))
                notes.append(self._parse_note_content(content, rel_path, p))
            except Exception:
                pass

        return sorted(notes, key=lambda n: n.title.lower())

    def get_note(self, name_or_path: str) -> Optional[VaultNote]:
        """Find and read a note by title, relative path, or filename."""
        clean = name_or_path.strip().replace(".md", "")
        # Direct path check
        p = self.vault_path / f"{clean}.md"
        if p.exists():
            content = p.read_text(encoding="utf-8", errors="replace")
            return self._parse_note_content(content, str(p.relative_to(self.vault_path)), p)

        # Search across folders
        for candidate in self.vault_path.rglob("*.md"):
            if ".obsidian" in candidate.parts:
                continue
            if candidate.stem.lower() == clean.lower() or str(candidate.relative_to(self.vault_path)).lower() == name_or_path.lower():
                content = candidate.read_text(encoding="utf-8", errors="replace")
                return self._parse_note_content(content, str(candidate.relative_to(self.vault_path)), candidate)

        return None

    def save_note(
        self,
        title: str,
        content: str,
        folder: str = "Ideas",
        tags: Optional[List[str]] = None,
    ) -> VaultNote:
        """Create or update a markdown note in the vault."""
        clean_title = re.sub(r'[<>:"/\\|?*]', "", title).strip()
        if not clean_title:
            clean_title = f"Untitled-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        target_dir = (self.vault_path / folder) if folder else self.vault_path
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"{clean_title}.md"

        full_content = content
        if tags:
            tag_line = "\n\n" + " ".join(f"#{t.lstrip('#')}" for t in tags)
            if tag_line.strip() not in full_content:
                full_content += tag_line

        file_path.write_text(full_content, encoding="utf-8")
        rel_path = str(file_path.relative_to(self.vault_path))
        return self._parse_note_content(full_content, rel_path, file_path)

    def delete_note(self, name_or_path: str) -> bool:
        """Delete a note from the vault."""
        note = self.get_note(name_or_path)
        if note and Path(note.abs_path).exists():
            Path(note.abs_path).unlink()
            return True
        return False

    def search_notes(self, query: str) -> List[VaultNote]:
        """Full-text search in note titles and contents."""
        q = query.strip().lower()
        if not q:
            return self.list_notes()

        results = []
        for note in self.list_notes():
            if q in note.title.lower() or q in note.content.lower() or any(q in t.lower() for t in note.tags):
                results.append(note)
        return results

    def get_daily_note(self, create_if_missing: bool = True) -> VaultNote:
        """Retrieve or create today's daily log note (Daily/YYYY-MM-DD.md)."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        daily_path = self.vault_path / "Daily" / f"{today_str}.md"

        if daily_path.exists():
            content = daily_path.read_text(encoding="utf-8", errors="replace")
        elif create_if_missing:
            daily_path.parent.mkdir(parents=True, exist_ok=True)
            content = (
                f"# 📅 Daily Note: {today_str}\n\n"
                f"Created at {datetime.now().strftime('%H:%M:%S')}.\n\n"
                "## 🎯 Goals & Focus\n"
                "- [ ] \n\n"
                "## 💡 Daily Logs & Ideas\n\n"
                "## 🧠 JARVIS Memory & Insights\n\n"
                "#daily #journal\n"
            )
            daily_path.write_text(content, encoding="utf-8")
        else:
            content = ""

        rel_path = str(daily_path.relative_to(self.vault_path))
        return self._parse_note_content(content, rel_path, daily_path)

    def get_graph_data(self) -> Dict[str, Any]:
        """Generate graph nodes and edges suitable for interactive canvas visualization."""
        notes = self.list_notes()
        nodes: List[Dict[str, Any]] = []
        edges: List[Tuple[str, str]] = []
        node_ids: Set[str] = set()

        # Center AI Core node
        nodes.append({
            "id": "ai-core",
            "label": "⚡ JARVIS AI Core",
            "type": "core",
            "group": "ai",
            "size": 18,
            "rel_path": "",
        })
        node_ids.add("ai-core")

        # Note nodes
        for note in notes:
            nid = note.title
            nodes.append({
                "id": nid,
                "label": note.title,
                "type": "note",
                "group": note.folder or "root",
                "size": max(10, min(16, 8 + note.word_count // 30)),
                "rel_path": note.rel_path,
                "tags": note.tags,
            })
            node_ids.add(nid)

            # Link to AI Core if related or in special folders
            if note.folder in ("Memories", "AI-Conversations"):
                edges.append(("ai-core", nid))

            # Inter-note wikilinks
            for target in note.links:
                edges.append((nid, target))

        # Tag nodes & clustering
        tag_map: Dict[str, List[str]] = {}
        for note in notes:
            for tag in note.tags:
                tag_map.setdefault(tag, []).append(note.title)

        for tag, tagged_notes in tag_map.items():
            if len(tagged_notes) > 1:
                tag_id = f"#{tag}"
                nodes.append({
                    "id": tag_id,
                    "label": tag_id,
                    "type": "tag",
                    "group": "tags",
                    "size": 8,
                    "rel_path": "",
                })
                node_ids.add(tag_id)
                for tn in tagged_notes:
                    edges.append((tn, tag_id))

        # Filter valid edges
        valid_edges = [
            {"source": src, "target": dst}
            for src, dst in edges
            if src in node_ids and dst in node_ids
        ]

        return {"nodes": nodes, "edges": valid_edges}

    def open_in_obsidian(self, rel_path: Optional[str] = None) -> bool:
        """Launch Obsidian with this vault, or open vault directory in Windows Explorer."""
        vault_name = self.vault_path.name
        uri = f"obsidian://open?vault={vault_name}"
        if rel_path:
            clean_file = rel_path.replace(".md", "").replace("\\", "/")
            uri += f"&file={clean_file}"

        # Attempt obsidian URI protocol first
        try:
            os.startfile(uri)
            return True
        except Exception:
            pass

        # Fallback: Open vault directory in Windows Explorer
        try:
            if os.name == "nt":
                os.startfile(str(self.vault_path))
            else:
                subprocess.Popen(["xdg-open", str(self.vault_path)])
            return True
        except Exception:
            return False
