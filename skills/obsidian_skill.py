"""Obsidian Vault and Note Skill for JARVIS.

Allows creating, searching, reading notes, managing daily journals, and
launching the Obsidian Knowledge Vault from voice, CLI, or GUI.
"""

from __future__ import annotations

import re
from typing import List, Optional

from core.registry import Skill
from core.types import ParsedCommand
from memory.vault import VaultManager, VaultNote


class ObsidianSkill(Skill):
    name = "Obsidian"
    triggers = ("obsidian", "vault", "note", "daily", "scan")
    help = (
        ("note <title>: <text>", "Save a note to the Obsidian vault"),
        ("vault scan / scan pc", "Scan and index all projects on A: and C: drives into the vault"),
        ("vault list [folder]", "List notes in the Obsidian vault"),
        ("vault search <query>", "Search notes and tags in the vault"),
        ("vault open / obsidian", "Open the vault in the native Obsidian app"),
        ("daily [text]", "View or append to today's daily journal"),
    )

    def __init__(self, vault: VaultManager) -> None:
        self.vault = vault

    def handle(self, command: ParsedCommand) -> str:
        verb, args = command.verb, command.args.strip()

        # ── obsidian / vault open ─────────────────────────────────────────────
        if verb == "obsidian" or (verb == "vault" and args.startswith("open")):
            target = args.replace("open", "").strip() or None
            opened = self.vault.open_in_obsidian(target)
            if opened:
                return "Opened Obsidian Knowledge Vault."
            return f"Vault located at: {self.vault.vault_path}"

        # ── note <title>: <content> or note <content> ─────────────────────────
        if verb == "note":
            if not args:
                return "What note would you like to create? Try: note Project Idea: Build a neural graph #ideas"
            
            # Check for title: content syntax
            if ":" in args:
                parts = args.split(":", 1)
                title = parts[0].strip()
                content = parts[1].strip()
            else:
                title = args[:40].strip()
                content = args

            saved = self.vault.save_note(title=title, content=content, folder="Ideas")
            return f"Saved note [[{saved.title}]] in vault ({saved.rel_path})."

        # ── daily [text] ──────────────────────────────────────────────────────
        if verb == "daily":
            daily_note = self.vault.get_daily_note(create_if_missing=True)
            if args:
                # Append to daily note
                new_content = daily_note.content.rstrip() + f"\n- {args}\n"
                self.vault.save_note(
                    title=daily_note.title,
                    content=new_content,
                    folder="Daily",
                )
                return f"Appended to daily note [[{daily_note.title}]]: {args}"
            return f"📅 [[{daily_note.title}]] ({daily_note.word_count} words):\n\n{daily_note.content[:400]}..."

        # ── vault list / search ───────────────────────────────────────────────
        if verb == "vault":
            if not args or args in ("list", "notes", "all"):
                notes = self.vault.list_notes()
                if not notes:
                    return f"Vault is empty at {self.vault.vault_path}."
                lines = [f"- [[{n.title}]] ({n.folder or 'root'})" for n in notes[:25]]
                if len(notes) > 25:
                    lines.append(f"... and {len(notes) - 25} more notes.")
                return f"Obsidian Vault ({len(notes)} notes):\n" + "\n".join(lines)

            if args.startswith("search"):
                query = args.replace("search", "", 1).strip()
                if not query:
                    return "Search for what in the vault? Try: vault search neural"
                results = self.vault.search_notes(query)
                if not results:
                    return f"No vault notes found matching '{query}'."
                lines = [f"- [[{n.title}]] ({n.folder}): {n.content[:60]}..." for n in results[:10]]
                return f"Found {len(results)} matching notes:\n" + "\n".join(lines)

            if args.startswith("list "):
                folder = args.replace("list", "", 1).strip()
                notes = self.vault.list_notes(folder=folder)
                if not notes:
                    return f"No notes found in folder '{folder}'."
                lines = [f"- [[{n.title}]]" for n in notes]
                return f"Notes in folder '{folder}' ({len(notes)}):\n" + "\n".join(lines)

        # ── vault scan / scan pc ──────────────────────────────────────────────
        if verb == "scan" or (verb == "vault" and args.startswith("scan")):
            from memory.pc_indexer import PCVaultIndexer
            indexer = PCVaultIndexer(self.vault)
            stats = indexer.index_all()
            return (
                f"✅ Scanned & Indexed Entire PC into Vault!\n"
                f"  * Drive A: {stats['drive_a']} project nodes\n"
                f"  * Drive C: {stats['drive_c']} workspace & tool nodes\n"
                f"  * Total Vault Nodes: {stats['total_nodes']}\n\n"
                "Open [[PC Master Knowledge Graph]] or press Ctrl+G in Obsidian to see your full PC Neural Graph!"
            )

        return "I don't recognize that Obsidian command. Try 'vault scan', 'note <title>: <text>', or 'vault open'."
