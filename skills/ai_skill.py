"""Natural-language conversation (roadmap v0.7).

This is the *fallback* skill: anything that isn't a recognised command is
sent here. It supports two providers out of the box and needs no extra
Python packages (it talks HTTP with the standard library):

* **Ollama** - a local model server (default). No API key, fully offline
  once a model is pulled.
* **OpenAI / OpenAI-compatible** - any endpoint that speaks the
  ``/chat/completions`` API.

If no provider is reachable or configured, the skill returns clear setup
instructions instead of raising, so the assistant stays usable offline.
Providers are small objects so a fake one can be injected in tests.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import List, Optional, Protocol

from core.registry import Skill
from core.types import ParsedCommand

Message = dict  # {"role": "system"|"user"|"assistant", "content": str}
_MAX_HISTORY = 20  # keep the last N turns to bound the prompt size


class ProviderError(Exception):
    """Raised when a provider can't produce a reply (with a human reason)."""


class ChatProvider(Protocol):
    def chat(self, messages: List[Message]) -> str: ...


def _post_json(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw_text = response.read().decode("utf-8")
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            # Fallback for SSE / chunked streams (data: {"choices": [{"delta": {"content": ...}}]})
            chunks = []
            for line in raw_text.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    chunk_data = line[5:].strip()
                    if chunk_data and chunk_data != "[DONE]":
                        try:
                            parsed = json.loads(chunk_data)
                            choices = parsed.get("choices") or []
                            if choices:
                                delta = choices[0].get("delta", {}).get("content") or choices[0].get("message", {}).get("content") or ""
                                if delta:
                                    chunks.append(delta)
                        except Exception:
                            pass
            if chunks:
                return {"choices": [{"message": {"content": "".join(chunks)}}]}
            raise ProviderError(f"Received non-JSON response: {raw_text[:200]}")


class OllamaProvider:
    def __init__(self, host: str, model: str, timeout: float) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, messages: List[Message]) -> str:
        url = f"{self.host}/api/chat"
        payload = {"model": self.model, "messages": messages, "stream": False}
        try:
            data = _post_json(url, payload, {}, self.timeout)
        except urllib.error.URLError as exc:
            raise ProviderError(
                f"can't reach Ollama at {self.host} ({exc.reason}). "
                "Is `ollama serve` running?"
            ) from exc
        return (data.get("message", {}) or {}).get("content", "").strip() or "(empty reply)"


class OpenAIProvider:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def chat(self, messages: List[Message]) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {"model": self.model, "messages": messages}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            data = _post_json(url, payload, headers, self.timeout)
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"the AI service returned HTTP {exc.code}.") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"can't reach the AI service ({exc.reason}).") from exc
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError("the AI service returned no choices.")
        return choices[0].get("message", {}).get("content", "").strip() or "(empty reply)"


def _normalize_omniroute_model(model: str) -> str:
    """Normalize model names so 'auto-best-free' maps to 'auto/best-free'."""
    if not model:
        return "auto/best-free"
    if "/" in model:
        return model
    prefixes = ("auto-", "meta-", "antigravity-", "nvidia-", "openrouter-", "kiro-", "ddgw-", "aug-")
    for p in prefixes:
        if model.startswith(p):
            return p[:-1] + "/" + model[len(p):]
    return model


class OmniRouteProvider:
    """Connects to OmniRoute gateway on port 20128 (330+ multi-provider AI profiles)."""

    def __init__(self, host: str, model: str, timeout: float) -> None:
        self.host = host.rstrip("/")
        self.model = _normalize_omniroute_model(model)
        self.timeout = timeout

    def chat(self, messages: List[Message]) -> str:
        url = f"{self.host}/chat/completions"
        payload = {"model": self.model, "messages": messages, "stream": False}
        headers = {"Authorization": "Bearer dummy"}
        try:
            data = _post_json(url, payload, headers, self.timeout)
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"OmniRoute returned HTTP {exc.code}.") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(
                f"can't reach OmniRoute at {self.host} ({exc.reason}). "
                "Is OmniRoute running? Run 'omniroute start' or launch via Launch-OmniRoute-Web.bat."
            ) from exc
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError("OmniRoute returned no choices.")
        return choices[0].get("message", {}).get("content", "").strip() or "(empty reply)"


class NullProvider:
    """Used when AI is disabled or misconfigured; always explains why."""

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def chat(self, messages: List[Message]) -> str:
        raise ProviderError(self.reason)


def make_provider(settings) -> ChatProvider:
    provider = (settings.ai_provider or "none").lower()
    if provider == "ollama":
        return OllamaProvider(settings.ollama_host, settings.ai_model, settings.ai_timeout)
    if provider in ("omniroute", "omni"):
        return OmniRouteProvider(settings.omniroute_host, settings.omniroute_model, settings.ai_timeout)
    if provider == "openai":
        if not settings.openai_api_key:
            return NullProvider("OpenAI is selected but OPENAI_API_KEY isn't set.")
        return OpenAIProvider(
            settings.openai_base_url,
            settings.openai_api_key,
            settings.openai_model,
            settings.ai_timeout,
        )
    return NullProvider("AI is turned off (set JARVIS_AI_PROVIDER=omniroute, ollama, or openai).")


class AISkill(Skill):
    name = "Assistant"
    triggers = ("ask", "chat", "ai")
    help = (
        ("ask <question>", "Ask the AI assistant something"),
        ("(anything else)", "Unrecognised input is sent to the AI assistant"),
    )
    is_fallback = True

    def __init__(self, provider: ChatProvider, settings, history: Optional[List[Message]] = None) -> None:
        self.provider = provider
        self.settings = settings
        self.history: List[Message] = history if history is not None else []

    def handle(self, command: ParsedCommand) -> str:
        # When invoked explicitly (ask/chat/ai) use the args; otherwise the
        # whole sentence the user typed.
        text = command.args if command.verb in self.triggers else command.raw
        text = text.strip()
        if not text:
            return "Ask me something, e.g. ask explain Python decorators."
        return self.reply(text)

    def reply(self, text: str) -> str:
        messages: List[Message] = [{"role": "system", "content": self.settings.system_prompt}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": text})
        try:
            answer = self.provider.chat(messages)
        except ProviderError as exc:
            return self._unavailable(str(exc))
        except Exception as exc:  # noqa: BLE001
            return self._unavailable(f"{type(exc).__name__}: {exc}")

        self.history.append({"role": "user", "content": text})
        self.history.append({"role": "assistant", "content": answer})
        if len(self.history) > _MAX_HISTORY:
            self.history = self.history[-_MAX_HISTORY:]
        return answer

    def _unavailable(self, reason: str) -> str:
        return (
            "The AI assistant isn't available right now.\n"
            f"Reason: {reason}\n\n"
            "To enable an AI provider:\n"
            "  * OmniRoute (330+ multi-model profiles): run 'omniroute start' (JARVIS_AI_PROVIDER=omniroute)\n"
            f"  * Ollama (local offline): run 'ollama pull {self.settings.ai_model}' and set JARVIS_AI_PROVIDER=ollama\n"
            "  * OpenAI: set OPENAI_API_KEY and JARVIS_AI_PROVIDER=openai."
        )
