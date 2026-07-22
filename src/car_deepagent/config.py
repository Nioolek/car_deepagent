from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from car_deepagent.paths import repo_root


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    timeout_ms: int
    thinking: bool = True


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_file_path() -> Path:
    override = os.environ.get("CAR_DEEPAGENT_ENV_FILE")
    if override:
        return Path(override)
    return repo_root() / ".env"


def load_settings() -> Settings:
    env_file = _env_file_path()
    override = bool(os.environ.get("CAR_DEEPAGENT_ENV_FILE"))
    load_dotenv(env_file, override=override)
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    base_url = os.environ.get("LLM_BASE_URL", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()
    timeout_raw = os.environ.get("LLM_TIMEOUT_MS", "60000").strip()
    thinking = _parse_bool(os.environ.get("LLM_THINKING"), default=True)
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
        thinking=thinking,
    )


def build_thinking_extra_body(thinking: bool) -> dict[str, Any] | None:
    """Request body fragment to enable model thinking / reasoning output."""
    if not thinking:
        return None
    return {"chat_template_kwargs": {"thinking": True}}


def _is_deepseek(settings: Settings) -> bool:
    blob = f"{settings.base_url} {settings.model}".lower()
    return "deepseek" in blob


def _deepseek_api_base(base_url: str) -> str:
    """ChatDeepSeek expects host root; strip trailing /v1 if present."""
    cleaned = base_url.rstrip("/")
    if cleaned.endswith("/v1"):
        return cleaned[: -len("/v1")]
    return cleaned


class ReasoningChatOpenAI(ChatOpenAI):
    """ChatOpenAI that surfaces OpenAI-compatible reasoning_content fields."""

    def _create_chat_result(
        self,
        response: dict | Any,
        generation_info: dict | None = None,
    ):
        result = super()._create_chat_result(response, generation_info)
        reasoning = _extract_reasoning_from_response(response)
        if reasoning and result.generations:
            message = result.generations[0].message
            message.additional_kwargs = {
                **(message.additional_kwargs or {}),
                "reasoning_content": reasoning,
            }
        return result

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ):
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk,
            default_chunk_class,
            base_generation_info,
        )
        if generation_chunk is None:
            return None
        reasoning = _extract_reasoning_from_chunk(chunk)
        if reasoning is not None:
            generation_chunk.message.additional_kwargs = {
                **(generation_chunk.message.additional_kwargs or {}),
                "reasoning_content": reasoning,
            }
        return generation_chunk


def _extract_reasoning_from_response(response: dict | Any) -> str | None:
    if isinstance(response, dict):
        choices = response.get("choices") or []
        if not choices:
            return None
        message = choices[0].get("message") or {}
        value = message.get("reasoning_content") or message.get("reasoning")
        return value if isinstance(value, str) and value.strip() else None

    choices = getattr(response, "choices", None) or []
    if not choices:
        return None
    message = getattr(choices[0], "message", None)
    if message is None:
        return None
    for attr in ("reasoning_content", "reasoning"):
        value = getattr(message, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    model_extra = getattr(message, "model_extra", None)
    if isinstance(model_extra, dict):
        value = model_extra.get("reasoning_content") or model_extra.get("reasoning")
        if isinstance(value, str) and value.strip():
            return value
    return None


def _extract_reasoning_from_chunk(chunk: dict) -> str | None:
    choices = chunk.get("choices") or []
    if not choices:
        return None
    delta = choices[0].get("delta") or {}
    value = delta.get("reasoning_content")
    if value is None:
        value = delta.get("reasoning")
    return value if isinstance(value, str) else None


def build_chat_model() -> BaseChatModel:
    s = load_settings()
    timeout_s = s.timeout_ms / 1000.0
    extra_body = build_thinking_extra_body(s.thinking)
    if _is_deepseek(s):
        from langchain_deepseek import ChatDeepSeek

        return ChatDeepSeek(
            model=s.model,
            api_key=s.api_key,
            api_base=_deepseek_api_base(s.base_url),
            timeout=timeout_s,
            extra_body=extra_body,
        )
    return ReasoningChatOpenAI(
        model=s.model,
        api_key=s.api_key,
        base_url=s.base_url,
        timeout=timeout_s,
        extra_body=extra_body,
    )
