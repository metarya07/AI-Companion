"""Coding agent: scaffold starter projects and classes.

Generation, explanation and debugging of arbitrary code are handled by
the AI assistant (just ask: "explain this code"). This skill covers the
deterministic, offline part - creating a tidy starting point.

Examples:
    scaffold python my_app
    scaffold java Student
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from core.registry import Skill
from core.types import ParsedCommand

_PY_MAIN = '''\
"""Entry point for {name}."""


def main() -> None:
    print("Hello from {name}!")


if __name__ == "__main__":
    main()
'''

_PY_TEST = '''\
from {name} import main


def test_main_runs(capsys):
    main.main()
    assert "Hello" in capsys.readouterr().out
'''

_PY_README = "# {name}\n\nA new Python project scaffolded by JARVIS.\n\n## Run\n\n    python -m {name}.main\n"

_JAVA_CLASS = '''\
public class {name} {{
    private String name;

    public {name}(String name) {{
        this.name = name;
    }}

    public String getName() {{
        return name;
    }}

    public void setName(String name) {{
        this.name = name;
    }}

    @Override
    public String toString() {{
        return "{name}{{name='" + name + "'}}";
    }}
}}
'''


class CodeSkill(Skill):
    name = "Coder"
    triggers = ("scaffold", "newproject")
    help = (
        ("scaffold python <name>", "Create a starter Python project"),
        ("scaffold java <ClassName>", "Create a starter Java class"),
    )

    def __init__(self, settings=None) -> None:
        self.settings = settings

    @property
    def _dry(self) -> bool:
        return bool(self.settings and getattr(self.settings, "dry_run", False))

    def handle(self, command: ParsedCommand) -> str:
        args = command.args.strip()
        if command.verb == "newproject":
            language, name = "python", args
        else:
            parts = args.split(maxsplit=1)
            language = parts[0].lower() if parts else ""
            name = parts[1].strip() if len(parts) > 1 else ""

        if not name:
            return "Name it, e.g. scaffold python my_app   or   scaffold java Student"

        if language == "python":
            return self._python(name)
        if language == "java":
            return self._java(name)
        return "Supported languages: python, java. e.g. scaffold python my_app"

    # --- generators ----------------------------------------------------------
    def _python(self, raw_name: str) -> str:
        name = raw_name.replace("-", "_").replace(" ", "_")
        root = Path.cwd() / name
        files: Dict[Path, str] = {
            root / name / "__init__.py": "",
            root / name / "main.py": _PY_MAIN.format(name=name),
            root / "tests" / f"test_{name}.py": _PY_TEST.format(name=name),
            root / "README.md": _PY_README.format(name=name),
            root / "requirements.txt": "",
        }
        return self._write(root, files, kind=f"Python project '{name}'")

    def _java(self, raw_name: str) -> str:
        # Java class names are conventionally PascalCase.
        name = "".join(part[:1].upper() + part[1:] for part in raw_name.replace("-", " ").split())
        target = Path.cwd() / f"{name}.java"
        files = {target: _JAVA_CLASS.format(name=name)}
        return self._write(target.parent, files, kind=f"Java class '{name}'", single=target)

    def _write(self, root: Path, files: Dict[Path, str], kind: str, single: Path = None) -> str:
        existing = single if (single and single.exists()) else (root if root.exists() and single is None else None)
        if existing is not None:
            return f"'{existing}' already exists - choose another name to avoid overwriting it."

        rel_base = Path.cwd()
        listing: List[str] = []
        for path in files:
            try:
                listing.append(str(path.relative_to(rel_base)))
            except ValueError:  # pragma: no cover
                listing.append(str(path))

        if self._dry:
            files_str = "\n".join(f"  {p}" for p in listing)
            return f"[dry-run] would create {kind}:\n{files_str}"

        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        files_str = "\n".join(f"  {p}" for p in listing)
        return f"Created {kind}:\n{files_str}"
