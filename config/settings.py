"""Runtime configuration for JARVIS.

Everything that used to be hard-coded (the database filename, the AI
provider, hosts, models, timeouts) now lives here and can be overridden
with environment variables. This keeps secrets out of the source tree
and makes the assistant easy to reconfigure without editing code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

# The project root is the directory that contains this package.
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PACKAGE_ROOT / "jarvis.db"
DEFAULT_VAULT_PATH = PACKAGE_ROOT / "vault"

DEFAULT_SYSTEM_PROMPT = (
    "You are JARVIS, a concise and friendly local desktop assistant. "
    "Answer clearly and get to the point. If you are unsure, say so."
)


def _as_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


@dataclass(frozen=True)
class Settings:
    """All tunable settings for a JARVIS session.

    Use :meth:`from_env` to build an instance from environment variables,
    or construct one directly (handy in tests).
    """

    db_path: Path = DEFAULT_DB_PATH
    vault_path: Path = DEFAULT_VAULT_PATH
    dry_run: bool = False  # when True, launchers describe instead of acting

    # AI provider: "omniroute" (multi-model router, default), "ollama" (local offline), "openai" (or compatible), or "none".
    ai_provider: str = "omniroute"
    ai_model: str = "llama3.2"
    ai_timeout: float = 60.0

    # Ollama (local) settings.
    ollama_host: str = "http://localhost:11434"

    # OpenAI / OpenAI-compatible settings.
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    # OmniRoute settings (multi-provider gateway on port 20128).
    omniroute_host: str = "http://localhost:20128/v1"
    omniroute_model: str = "auto-best-free"
    omniroute_auto_start: bool = True

    system_prompt: str = DEFAULT_SYSTEM_PROMPT

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Settings":
        env = env if env is not None else os.environ
        return cls(
            db_path=Path(env.get("JARVIS_DB_PATH", str(DEFAULT_DB_PATH))),
            vault_path=Path(env.get("JARVIS_VAULT_PATH", str(DEFAULT_VAULT_PATH))),
            dry_run=_as_bool(env.get("JARVIS_DRY_RUN"), False),
            ai_provider=env.get("JARVIS_AI_PROVIDER", "omniroute").strip().lower(),
            ai_model=env.get("JARVIS_AI_MODEL", "llama3.2"),
            ai_timeout=float(env.get("JARVIS_AI_TIMEOUT", "60")),
            ollama_host=env.get("JARVIS_OLLAMA_HOST", "http://localhost:11434").rstrip("/"),
            openai_base_url=env.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            openai_api_key=env.get("OPENAI_API_KEY") or None,
            openai_model=env.get("OPENAI_MODEL", "gpt-4o-mini"),
            omniroute_host=env.get("JARVIS_OMNIROUTE_HOST", "http://localhost:20128/v1").rstrip("/"),
            omniroute_model=env.get("JARVIS_OMNIROUTE_MODEL", "auto-best-free"),
            omniroute_auto_start=_as_bool(env.get("JARVIS_OMNIROUTE_AUTO_START"), True),
            system_prompt=env.get("JARVIS_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
        )
