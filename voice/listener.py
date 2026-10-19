"""Voice input/output (roadmap v0.6).

Optional feature built on ``SpeechRecognition`` (+ a microphone backend
such as PyAudio) and ``pyttsx3`` for speech. Everything is imported
lazily and failures degrade gracefully, so the rest of JARVIS works even
when these packages or a microphone aren't present.
"""

from __future__ import annotations

from typing import Optional


class VoiceUnavailable(Exception):
    """Raised when speech recognition can't be initialised."""


class VoiceListener:
    def __init__(self) -> None:
        try:
            import speech_recognition as sr  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise VoiceUnavailable(
                "Voice mode needs extra packages:\n"
                "  pip install SpeechRecognition PyAudio pyttsx3"
            ) from exc

        self._sr = sr
        self._recognizer = sr.Recognizer()
        try:
            self._microphone = sr.Microphone()
        except Exception as exc:  # pragma: no cover - no mic / no PyAudio
            raise VoiceUnavailable(
                f"No microphone available ({exc}). Install PyAudio and check your mic."
            ) from exc

        self._tts = self._make_tts()

    @staticmethod
    def _make_tts():  # pragma: no cover - hardware/engine dependent
        try:
            import pyttsx3  # type: ignore

            return pyttsx3.init()
        except Exception:
            return None

    def listen_once(self) -> Optional[str]:  # pragma: no cover - needs a mic
        """Record one phrase and return the transcription (or None)."""
        with self._microphone as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=0.4)
            audio = self._recognizer.listen(source)
        try:
            return self._recognizer.recognize_google(audio)
        except self._sr.UnknownValueError:
            return None
        except self._sr.RequestError:
            return None

    def speak(self, text: str) -> None:  # pragma: no cover - needs an audio device
        if not self._tts:
            return
        self._tts.say(text)
        self._tts.runAndWait()
