"""PC Knowledge Vault Indexer for JARVIS.

Scans, categorizes, and generates rich Obsidian Markdown notes for projects,
workspaces, developer tools, and data across both Drive A: and Drive C:.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from memory.vault import VaultManager


def _format_size(num_bytes: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def _get_dir_size_fast(path: Path, max_depth: int = 2) -> Tuple[int, int]:
    """Calculate directory size and file count quickly without hanging on deep trees."""
    total_size = 0
    file_count = 0
    ignore_dirs = {
        "node_modules", ".git", "venv", ".venv", "__pycache__", "build", "dist",
        ".gradle", ".cache", "AppData", "Windows", "Program Files", "Program Files (x86)",
    }
    try:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
            depth = len(Path(root).relative_to(path).parts)
            if depth > max_depth:
                dirs[:] = []
                continue
            for f in files:
                try:
                    fp = os.path.join(root, f)
                    total_size += os.path.getsize(fp)
                    file_count += 1
                except Exception:
                    pass
    except Exception:
        pass
    return total_size, file_count


def _detect_tech_stack(path: Path) -> List[str]:
    """Detect technologies used in a directory based on signature files."""
    tags = []
    try:
        names = {p.name.lower() for p in path.iterdir() if not p.name.startswith(".")}
        if any(n.endswith((".py", ".pyw")) or n in ("requirements.txt", "pyproject.toml", "setup.py") for n in names):
            tags.append("python")
        if any(n.endswith((".js", ".jsx", ".ts", ".tsx")) or n in ("package.json", "tsconfig.json") for n in names):
            tags.append("javascript")
        if any(n.endswith((".java", ".jar", ".class")) or n in ("pom.xml", "build.gradle") for n in names):
            tags.append("java")
        if any(n.endswith((".rs",)) or n == "cargo.toml" for n in names):
            tags.append("rust")
        if any(n.endswith((".go",)) or n == "go.mod" for n in names):
            tags.append("golang")
        if any(n.endswith((".html", ".css")) for n in names):
            tags.append("web")
        if any(n.endswith((".bat", ".ps1", ".sh", ".cmd")) for n in names):
            tags.append("automation")
    except Exception:
        pass
    return tags or ["project"]


class PCVaultIndexer:
    """Scans Drive A: and Drive C: and indexes them into the Obsidian Vault."""

    def __init__(self, vault: VaultManager) -> None:
        self.vault = vault

    def index_all(self) -> Dict[str, int]:
        """Run full scan on A: and C: and generate Obsidian notes."""
        stats = {"drive_a": 0, "drive_c": 0, "total_nodes": 0}

        # ── Scan Drive A: ─────────────────────────────────────────────────────
        a_projects = self._scan_drive_a_projects()
        a_top_dirs = self._scan_drive_a_top()
        stats["drive_a"] = len(a_projects) + len(a_top_dirs)

        # ── Scan Drive C: ─────────────────────────────────────────────────────
        c_workspaces = self._scan_drive_c_workspaces()
        c_ai_configs = self._scan_drive_c_ai_tools()
        stats["drive_c"] = len(c_workspaces) + len(c_ai_configs)

        # ── Create Drive Hub Notes & Master Graph ─────────────────────────────
        self._create_drive_a_hub(a_projects, a_top_dirs)
        self._create_drive_c_hub(c_workspaces, c_ai_configs)
        self._create_master_system_graph(a_projects, c_workspaces)

        stats["total_nodes"] = len(self.vault.list_notes())
        return stats

    def _scan_drive_a_projects(self) -> List[Dict[str, Any]]:
        projects_dir = Path(r"A:\Projects")
        results = []
        if not projects_dir.exists():
            return results

        for item in sorted(projects_dir.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                size, files = _get_dir_size_fast(item)
                tech = _detect_tech_stack(item)
                title = f"Project - {item.name}"
                mod_time = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

                content = (
                    f"# 🚀 {item.name}\n\n"
                    f"**Location:** `{str(item)}`\n"
                    f"**Drive:** `A:\\` | **Type:** Project Workspace\n"
                    f"**Last Modified:** {mod_time}\n"
                    f"**Size:** {_format_size(size)} ({files} scanned files)\n\n"
                    "## 🛠️ Tech Stack & Tags\n"
                    + " ".join(f"#{t}" for t in tech)
                    + " #drive-a #project\n\n"
                    "## 🔗 Connections & Navigation\n"
                    "- [[Drive-A Knowledge Hub]]\n"
                    "- [[PC Master Knowledge Graph]]\n"
                    "- [[JARVIS Neural Knowledge Vault]]\n"
                )

                self.vault.save_note(title=title, content=content, folder="Drive-A", tags=tech + ["drive-a"])
                results.append({"name": item.name, "title": title, "path": str(item), "size": size, "tech": tech})

        return results

    def _scan_drive_a_top(self) -> List[Dict[str, Any]]:
        a_root = Path(r"A:\\")
        results = []
        skip = {"$RECYCLE.BIN", "System Volume Information", "Projects", "vault", "tmp", "blobs"}
        if not a_root.exists():
            return results

        for item in sorted(a_root.iterdir()):
            if item.is_dir() and item.name not in skip and not item.name.startswith("."):
                size, files = _get_dir_size_fast(item)
                title = f"Workspace - {item.name}"
                mod_time = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

                content = (
                    f"# 📁 {item.name} (Drive A Root)\n\n"
                    f"**Location:** `{str(item)}`\n"
                    f"**Type:** Top-level Workspace / Directory\n"
                    f"**Last Modified:** {mod_time}\n"
                    f"**Size:** {_format_size(size)} ({files} files)\n\n"
                    "## 🔗 Connected Hubs\n"
                    "- [[Drive-A Knowledge Hub]]\n"
                    "- [[PC Master Knowledge Graph]]\n\n"
                    "#drive-a #workspace\n"
                )

                self.vault.save_note(title=title, content=content, folder="Drive-A", tags=["drive-a", "workspace"])
                results.append({"name": item.name, "title": title, "path": str(item), "size": size})

        return results

    def _scan_drive_c_workspaces(self) -> List[Dict[str, Any]]:
        user_dir = Path.home()
        candidates = [
            "AndroidStudioProjects", "secure-file-management-system", "Qwiz",
            "Documents", "Desktop", "Downloads", "Cisco Packet Tracer 9.0.0",
        ]
        results = []
        for name in candidates:
            p = user_dir / name
            if p.exists() and p.is_dir():
                size, files = _get_dir_size_fast(p)
                tech = _detect_tech_stack(p)
                title = f"User - {name}"
                mod_time = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

                content = (
                    f"# 💻 {name} (Drive C User Directory)\n\n"
                    f"**Location:** `{str(p)}`\n"
                    f"**Drive:** `C:\\` | **Type:** User Workspace / Data\n"
                    f"**Last Modified:** {mod_time}\n"
                    f"**Size:** {_format_size(size)} ({files} scanned files)\n\n"
                    "## 🛠️ Stack & Categories\n"
                    + " ".join(f"#{t}" for t in tech)
                    + " #drive-c #user-space\n\n"
                    "## 🔗 Connected Hubs\n"
                    "- [[Drive-C Knowledge Hub]]\n"
                    "- [[PC Master Knowledge Graph]]\n"
                )

                self.vault.save_note(title=title, content=content, folder="Drive-C", tags=tech + ["drive-c"])
                results.append({"name": name, "title": title, "path": str(p), "size": size, "tech": tech})

        return results

    def _scan_drive_c_ai_tools(self) -> List[Dict[str, Any]]:
        user_dir = Path.home()
        tools = [
            (".claude", "Claude Code Multi-Profile Configurations", ["claude", "ai"]),
            (".omniroute", "OmniRoute AI Multi-Model Gateway Data & SQLite", ["omniroute", "gateway", "ai"]),
            (".ollama", "Ollama Local Offline AI Models", ["ollama", "local-ai"]),
            (".gemini", "Antigravity & Gemini Developer Agent Configurations", ["antigravity", "gemini", "ai"]),
            (".vscode", "Visual Studio Code User Settings & Extensions", ["vscode", "ide"]),
        ]
        results = []
        for dirname, desc, tags in tools:
            p = user_dir / dirname
            if p.exists():
                size, files = _get_dir_size_fast(p, max_depth=1)
                title = f"Tool - {dirname.lstrip('.')}"
                content = (
                    f"# ⚙️ {desc}\n\n"
                    f"**Directory:** `{str(p)}`\n"
                    f"**Size:** {_format_size(size)}\n\n"
                    "## 🔗 Connected Hubs\n"
                    "- [[Drive-C Knowledge Hub]]\n"
                    "- [[PC Master Knowledge Graph]]\n\n"
                    + " ".join(f"#{t}" for t in tags)
                    + " #tools #developer\n"
                )
                self.vault.save_note(title=title, content=content, folder="Drive-C", tags=tags)
                results.append({"name": dirname, "title": title, "path": str(p), "desc": desc})

        return results

    def _create_drive_a_hub(self, projects: List[dict], top_dirs: List[dict]):
        proj_links = "\n".join(f"- [[{p['title']}]] — `{p['name']}` ({_format_size(p['size'])})" for p in projects)
        dir_links = "\n".join(f"- [[{d['title']}]] — `{d['name']}`" for d in top_dirs)

        content = (
            "# 💽 Drive A: Knowledge & Project Hub\n\n"
            f"Indexed at {datetime.now().strftime('%Y-%m-%d %H:%M')}.\n\n"
            "## 🚀 Projects (`A:\\Projects`)\n"
            f"{proj_links}\n\n"
            "## 📁 Workspaces & Tools (`A:\\`)\n"
            f"{dir_links}\n\n"
            "## 🔗 Connected Hubs\n"
            "- [[PC Master Knowledge Graph]]\n"
            "- [[Drive-C Knowledge Hub]]\n"
            "- [[JARVIS Neural Knowledge Vault]]\n\n"
            "#drive-a #hub #knowledge-graph\n"
        )
        self.vault.save_note(title="Drive-A Knowledge Hub", content=content, folder="Drive-A")

    def _create_drive_c_hub(self, workspaces: List[dict], tools: List[dict]):
        ws_links = "\n".join(f"- [[{w['title']}]] — `{w['name']}` ({_format_size(w['size'])})" for w in workspaces)
        tool_links = "\n".join(f"- [[{t['title']}]] — {t['desc']}" for t in tools)

        content = (
            "# 💻 Drive C: User Space & AI Tool Hub\n\n"
            f"Indexed at {datetime.now().strftime('%Y-%m-%d %H:%M')}.\n\n"
            "## 📂 User Workspaces (`C:\\Users\\metar`)\n"
            f"{ws_links}\n\n"
            "## 🤖 AI Engines & Developer Tools\n"
            f"{tool_links}\n\n"
            "## 🔗 Connected Hubs\n"
            "- [[PC Master Knowledge Graph]]\n"
            "- [[Drive-A Knowledge Hub]]\n"
            "- [[JARVIS Neural Knowledge Vault]]\n\n"
            "#drive-c #hub #knowledge-graph\n"
        )
        self.vault.save_note(title="Drive-C Knowledge Hub", content=content, folder="Drive-C")

    def _create_master_system_graph(self, a_projects: List[dict], c_workspaces: List[dict]):
        content = (
            "# 🧠 PC Master Knowledge Graph (Unified Drives A: & C:)\n\n"
            "Central node mapping all computing resources, codebases, AI models, and memory.\n\n"
            "## 🌐 Primary Hubs\n"
            "- [[Drive-A Knowledge Hub]] — Primary Development Projects & Storage\n"
            "- [[Drive-C Knowledge Hub]] — Operating System, AI Tools & User Space\n"
            "- [[JARVIS Neural Knowledge Vault]] — AI Operating Core & Memories\n"
            "- [[Daily Tasks]] — Active Action Items\n\n"
            "## ⚡ Quick Navigation\n"
            f"- **A: Drive Projects ({len(a_projects)}):** "
            + ", ".join(f"[[{p['title']}]]" for p in a_projects[:6])
            + f" ... and {max(0, len(a_projects) - 6)} more.\n"
            f"- **C: Drive Workspaces ({len(c_workspaces)}):** "
            + ", ".join(f"[[{w['title']}]]" for w in c_workspaces)
            + "\n\n"
            "#master-graph #second-brain #neural-network\n"
        )
        self.vault.save_note(title="PC Master Knowledge Graph", content=content, folder="Ideas")
