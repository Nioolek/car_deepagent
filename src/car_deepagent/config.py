from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from car_deepagent.paths import repo_root


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    timeout_ms: int


def _env_file_path() -> Path:
    override = os.environ.get("CAR_DEEPAGENT_ENV_FILE")
    if override:
        return Path(override)
    return repo_root() / ".env"


def load_settings() -> Settings:
    load_dotenv(_env_file_path(), override=False)
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    base_url = os.environ.get("LLM_BASE_URL", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()
    timeout_raw = os.environ.get("LLM_TIMEOUT_MS", "60000").strip()
    if not api_key or not base_url or not model:
        raise RuntimeError(
            "Missing LLM_API_KEY / LLM_BASE_URL / LLM_MODEL in .env "
            f"(looked at {_env_file_path()})"
        )
    return Settings(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_ms=int(timeout_raw),
    )


def build_chat_model() -> ChatOpenAI:
    s = load_settings()
    return ChatOpenAI(
        model=s.model,
        api_key=s.api_key,
        base_url=s.base_url,
        timeout=s.timeout_ms / 1000.0,
    )
