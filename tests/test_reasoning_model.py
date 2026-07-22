from types import SimpleNamespace

from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI

from car_deepagent.config import (
    ReasoningChatOpenAI,
    Settings,
    _deepseek_api_base,
    _extract_reasoning_from_chunk,
    _extract_reasoning_from_response,
    _is_deepseek,
    build_chat_model,
    build_thinking_extra_body,
)


def test_deepseek_api_base_strips_v1():
    assert _deepseek_api_base("https://api.deepseek.com/v1") == (
        "https://api.deepseek.com"
    )
    assert _deepseek_api_base("https://api.deepseek.com/") == (
        "https://api.deepseek.com"
    )


def test_is_deepseek_detects_url_or_model():
    assert _is_deepseek(
        Settings("k", "https://api.deepseek.com/v1", "deepseek-v4-flash", 1)
    )
    assert _is_deepseek(Settings("k", "https://example.com/v1", "deepseek-r1", 1))
    assert not _is_deepseek(Settings("k", "https://example.com/v1", "gpt-4o", 1))


def test_extract_reasoning_from_response_dict_and_object():
    assert (
        _extract_reasoning_from_response(
            {
                "choices": [
                    {"message": {"content": "hi", "reasoning_content": "think"}}
                ]
            }
        )
        == "think"
    )
    message = SimpleNamespace(reasoning_content="step", reasoning=None, model_extra=None)
    choice = SimpleNamespace(message=message)
    response = SimpleNamespace(choices=[choice])
    assert _extract_reasoning_from_response(response) == "step"


def test_extract_reasoning_from_chunk():
    assert (
        _extract_reasoning_from_chunk(
            {"choices": [{"delta": {"reasoning_content": "partial"}}]}
        )
        == "partial"
    )
    assert _extract_reasoning_from_chunk({"choices": [{"delta": {}}]}) is None


def test_build_thinking_extra_body():
    assert build_thinking_extra_body(True) == {
        "chat_template_kwargs": {"thinking": True},
    }
    assert build_thinking_extra_body(False) is None


def test_build_chat_model_uses_deepseek(monkeypatch):
    monkeypatch.setattr(
        "car_deepagent.config.load_settings",
        lambda: Settings(
            "k",
            "https://api.deepseek.com/v1",
            "deepseek-v4-flash",
            5000,
            thinking=True,
        ),
    )
    model = build_chat_model()
    assert isinstance(model, ChatDeepSeek)
    assert model.extra_body == {"chat_template_kwargs": {"thinking": True}}


def test_build_chat_model_uses_reasoning_openai(monkeypatch):
    monkeypatch.setattr(
        "car_deepagent.config.load_settings",
        lambda: Settings("k", "https://example.com/v1", "gpt-4o", 5000, thinking=True),
    )
    model = build_chat_model()
    assert isinstance(model, ReasoningChatOpenAI)
    assert isinstance(model, ChatOpenAI)
    assert model.extra_body == {"chat_template_kwargs": {"thinking": True}}
