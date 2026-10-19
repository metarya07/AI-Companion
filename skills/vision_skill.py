"""Screen capture and on-screen text reading (roadmap v0.8).

Optional feature: it imports its dependencies lazily and, if they aren't
installed (or there's no display), returns a helpful message instead of
crashing. With ``mss`` + ``Pillow`` it can grab a screenshot, and with
``pytesseract`` (plus the Tesseract binary) it can read the text on it.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from core.registry import Skill
from core.types import ParsedCommand


class VisionSkill(Skill):
    name = "Vision"
    triggers = ("screen", "screenshot", "ocr")
    help = (
        ("screen", "Read the text currently visible on screen (OCR)"),
        ("screenshot", "Save a screenshot to your home folder"),
    )

    def __init__(self, settings=None) -> None:
        self.settings = settings

    def handle(self, command: ParsedCommand) -> str:
        image = self._capture()
        if isinstance(image, str):  # capture returned an error message
            return image

        if command.verb in ("screen", "ocr"):
            return self._read_text(image)
        return self._save(image)

    # --- helpers -------------------------------------------------------------
    def _capture(self):
        try:
            import mss  # type: ignore
            from PIL import Image  # type: ignore
        except ImportError:
            return (
                "Vision needs a couple of extra packages:\n"
                "  pip install mss pillow pytesseract"
            )
        try:
            with mss.mss() as sct:
                shot = sct.grab(sct.monitors[0])
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        except Exception as exc:  # noqa: BLE001 - e.g. no display available
            return f"Couldn't capture the screen: {exc}"

    def _read_text(self, image) -> str:
        try:
            import pytesseract  # type: ignore
        except ImportError:
            return (
                "OCR needs pytesseract and the Tesseract engine:\n"
                "  pip install pytesseract  (and install Tesseract for your OS)"
            )
        try:
            text = pytesseract.image_to_string(image).strip()
        except Exception as exc:  # noqa: BLE001
            return f"OCR failed: {exc}"
        if not text:
            return "I captured the screen but couldn't find any readable text."
        return "Text detected on screen:\n" + text

    def _save(self, image) -> str:
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = Path.home() / f"jarvis-screenshot-{stamp}.png"
        try:
            image.save(path)
        except Exception as exc:  # noqa: BLE001
            return f"Couldn't save the screenshot: {exc}"
        return f"Screenshot saved to {path}"
