"""FilesSkill: real (but isolated) file operations under tmp_path."""

from __future__ import annotations

from config.settings import Settings
from core.types import ParsedCommand
from skills.files_skill import FilesSkill


def _skill(dry: bool = False) -> FilesSkill:
    return FilesSkill(Settings(dry_run=dry))


def _cmd(verb: str, args: str) -> ParsedCommand:
    return ParsedCommand(raw=f"{verb} {args}".strip(), verb=verb, args=args)


def test_ls_lists_entries(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "sub").mkdir()
    out = _skill().handle(_cmd("ls", str(tmp_path)))
    assert "a.txt" in out and "sub" in out


def test_ls_missing_folder():
    out = _skill().handle(_cmd("ls", "/no/such/place/xyz"))
    assert "No such folder" in out


def test_find_by_pattern(tmp_path):
    (tmp_path / "a.pdf").write_text("x")
    (tmp_path / "b.txt").write_text("x")
    out = _skill().handle(_cmd("find", f"*.pdf in {tmp_path}"))
    assert "a.pdf" in out and "b.txt" not in out


def test_move(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("data")
    dst = tmp_path / "dst.txt"
    out = _skill().handle(_cmd("move", f"{src} {dst}"))
    assert dst.exists() and not src.exists()
    assert "Moved" in out


def test_copy(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("data")
    dst = tmp_path / "copy.txt"
    _skill().handle(_cmd("copy", f"{src} {dst}"))
    assert src.exists() and dst.exists()


def test_organize_sorts_by_type(tmp_path):
    (tmp_path / "pic.png").write_text("x")
    (tmp_path / "doc.pdf").write_text("x")
    (tmp_path / "song.mp3").write_text("x")
    (tmp_path / "weird.xyz").write_text("x")
    out = _skill().handle(_cmd("organize", str(tmp_path)))
    assert (tmp_path / "images" / "pic.png").exists()
    assert (tmp_path / "documents" / "doc.pdf").exists()
    assert (tmp_path / "audio" / "song.mp3").exists()
    assert (tmp_path / "others" / "weird.xyz").exists()
    assert "Organized" in out


def test_clean_sweeps_into_dated_folder(tmp_path):
    (tmp_path / "loose1.txt").write_text("x")
    (tmp_path / "loose2.txt").write_text("x")
    out = _skill().handle(_cmd("clean", str(tmp_path)))
    assert "Swept" in out
    swept = [p for p in tmp_path.iterdir() if p.is_dir() and p.name.startswith("cleaned-")]
    assert len(swept) == 1
    assert len(list(swept[0].iterdir())) == 2


def test_backup_creates_zip(tmp_path):
    folder = tmp_path / "notes"
    folder.mkdir()
    (folder / "n.txt").write_text("hello")
    out = _skill().handle(_cmd("backup", str(folder)))
    zips = list(tmp_path.glob("notes-backup-*.zip"))
    assert len(zips) == 1
    assert "Backed up" in out


def test_dry_run_does_not_move(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("data")
    dst = tmp_path / "dst.txt"
    out = _skill(dry=True).handle(_cmd("move", f"{src} {dst}"))
    assert out.startswith("[dry-run]")
    assert src.exists() and not dst.exists()
