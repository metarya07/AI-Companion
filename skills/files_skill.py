"""Computer-control agent: safe file management.

Every operation is non-destructive (nothing is ever deleted - "clean"
sweeps loose files into a dated folder) and respects ``JARVIS_DRY_RUN``,
so you can preview before anything moves.

Examples:
    ls ~/Downloads
    find *.pdf in ~/Documents
    move report.pdf ~/Documents
    copy notes.txt backup.txt
    organize ~/Downloads        (sort files into images/, documents/, ...)
    clean ~/Downloads           (sweep loose files into a dated subfolder)
    backup ~/notes              (zip the folder next to itself)
"""

from __future__ import annotations

import datetime as _dt
import os
import shlex
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.registry import Skill
from core.types import ParsedCommand

_MAX_LIST = 40

# Map file extensions to the folder name used by "organize".
_CATEGORIES: Dict[str, Tuple[str, ...]] = {
    "images": (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".heic"),
    "documents": (".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt",
                  ".ppt", ".pptx", ".xls", ".xlsx", ".csv"),
    "audio": (".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"),
    "video": (".mp4", ".mkv", ".mov", ".avi", ".webm"),
    "archives": (".zip", ".tar", ".gz", ".tgz", ".rar", ".7z"),
    "code": (".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go",
             ".rs", ".rb", ".sh", ".html", ".css", ".json", ".yaml", ".yml"),
}
_CATEGORY_NAMES = set(_CATEGORIES) | {"others"}


def _category(suffix: str) -> str:
    suffix = suffix.lower()
    for name, exts in _CATEGORIES.items():
        if suffix in exts:
            return name
    return "others"


class FilesSkill(Skill):
    name = "Files"
    triggers = ("files", "ls", "find", "move", "copy", "organize", "clean", "backup")
    help = (
        ("ls [path]", "List files in a folder"),
        ("find <pattern> [in <path>]", "Find files matching a pattern"),
        ("move <src> <dst>", "Move a file or folder"),
        ("copy <src> <dst>", "Copy a file or folder"),
        ("organize [path]", "Sort files into type folders (images, documents...)"),
        ("clean [path]", "Sweep loose files into a dated folder (nothing deleted)"),
        ("backup <path>", "Zip a folder next to itself"),
    )

    def __init__(self, settings=None) -> None:
        self.settings = settings

    @property
    def _dry(self) -> bool:
        return bool(self.settings and getattr(self.settings, "dry_run", False))

    def handle(self, command: ParsedCommand) -> str:
        verb, args = command.verb, command.args.strip()
        if verb == "files":
            return "File commands: ls, find, move, copy, organize, clean, backup. Try 'help'."
        if verb == "ls":
            return self._ls(args or ".")
        if verb == "find":
            return self._find(args)
        if verb in ("move", "copy"):
            return self._transfer(verb, args)
        if verb == "organize":
            return self._organize(args or ".")
        if verb == "clean":
            return self._clean(args or ".")
        if verb == "backup":
            return self._backup(args)
        return "I don't understand that file command."

    # --- helpers -------------------------------------------------------------
    @staticmethod
    def _resolve(text: str) -> Path:
        return Path(text).expanduser()

    def _ls(self, path_text: str) -> str:
        path = self._resolve(path_text)
        if not path.exists():
            return f"No such folder: {path}"
        if not path.is_dir():
            return f"{path} is a file, not a folder."
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        if not entries:
            return f"{path} is empty."
        shown = entries[:_MAX_LIST]
        lines = [f"{'📁' if e.is_dir() else '  '} {e.name}" for e in shown]
        if len(entries) > _MAX_LIST:
            lines.append(f"... and {len(entries) - _MAX_LIST} more")
        return "\n".join(lines)

    def _find(self, args: str) -> str:
        if not args:
            return "Find what? e.g. find *.pdf in ~/Documents"
        low = args.lower()
        if " in " in low:
            idx = low.rfind(" in ")
            pattern = args[:idx].strip()
            root = self._resolve(args[idx + 4:].strip())
        else:
            pattern, root = args.strip(), Path.cwd()
        if not root.exists():
            return f"No such folder: {root}"
        matches = []
        for p in root.rglob(pattern):
            matches.append(p)
            if len(matches) >= _MAX_LIST:
                break
        if not matches:
            return f"No files matching '{pattern}' under {root}."
        rel = [str(p.relative_to(root)) for p in matches]
        out = "\n".join(rel)
        if len(matches) >= _MAX_LIST:
            out += f"\n... (showing first {_MAX_LIST})"
        return out

    def _transfer(self, verb: str, args: str) -> str:
        try:
            parts = shlex.split(args, posix=(os.name != "nt"))
        except ValueError:
            parts = args.split()
        if len(parts) != 2:
            return f"Use: {verb} <src> <dst>   (quote paths with spaces)"
        src = self._resolve(parts[0])
        dst = self._resolve(parts[1])
        if not src.exists():
            return f"Source not found: {src}"
        action = "move" if verb == "move" else "copy"
        if self._dry:
            return f"[dry-run] would {action} {src} -> {dst}"
        try:
            if verb == "move":
                shutil.move(str(src), str(dst))
            elif src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        except Exception as exc:  # noqa: BLE001
            return f"Couldn't {action} {src.name}: {exc}"
        return f"{action.capitalize()}d {src.name} -> {dst}"

    def _top_level_files(self, path: Path) -> List[Path]:
        return [
            p for p in path.iterdir()
            if p.is_file() and not p.name.startswith(".")
        ]

    def _organize(self, path_text: str) -> str:
        path = self._resolve(path_text)
        if not path.is_dir():
            return f"No such folder: {path}"
        files = [p for p in self._top_level_files(path)]
        if not files:
            return f"Nothing to organize in {path}."
        counts: Dict[str, int] = {}
        for f in files:
            category = _category(f.suffix)
            counts[category] = counts.get(category, 0) + 1
            if not self._dry:
                target_dir = path / category
                target_dir.mkdir(exist_ok=True)
                try:
                    shutil.move(str(f), str(target_dir / f.name))
                except Exception:  # noqa: BLE001 - skip files that won't move
                    counts[category] -= 1
        summary = ", ".join(f"{n} -> {name}/" for name, n in sorted(counts.items()) if n)
        prefix = "[dry-run] would organize" if self._dry else "Organized"
        return f"{prefix} {sum(counts.values())} file(s) in {path}: {summary}"

    def _clean(self, path_text: str) -> str:
        path = self._resolve(path_text)
        if not path.is_dir():
            return f"No such folder: {path}"
        files = self._top_level_files(path)
        if not files:
            return f"Nothing to clean in {path}."
        stamp = _dt.datetime.now().strftime("%Y%m%d")
        target = path / f"cleaned-{stamp}"
        if self._dry:
            return f"[dry-run] would sweep {len(files)} file(s) into {target}"
        target.mkdir(exist_ok=True)
        moved = 0
        for f in files:
            try:
                shutil.move(str(f), str(target / f.name))
                moved += 1
            except Exception:  # noqa: BLE001
                pass
        return f"Swept {moved} file(s) into {target} (nothing deleted)."

    def _backup(self, path_text: str) -> str:
        if not path_text:
            return "Back up what? e.g. backup ~/notes"
        path = self._resolve(path_text)
        if not path.is_dir():
            return f"No such folder: {path}"
        stamp = _dt.datetime.now().strftime("%Y%m%d")
        base = path.parent / f"{path.name}-backup-{stamp}"
        if self._dry:
            return f"[dry-run] would create {base}.zip from {path}"
        try:
            archive = shutil.make_archive(str(base), "zip", root_dir=str(path))
        except Exception as exc:  # noqa: BLE001
            return f"Couldn't back up {path}: {exc}"
        return f"Backed up {path} -> {archive}"
