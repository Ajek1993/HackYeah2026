import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from openai import APITimeoutError

from app.config import settings
from app.llm import GLMClient, LLMUnavailableError

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": "Resolve an address",
            "parameters": {"type": "object", "properties": {"q": {"type": "string"}}},
        },
    }
]
MESSAGES = [{"role": "user", "content": "Test question"}]


def make_openai_mock(content: str = "{}") -> MagicMock:
    mock = MagicMock()
    message = SimpleNamespace(role="assistant", content=content, tool_calls=None)
    mock.chat.completions.create = AsyncMock(
        return_value=SimpleNamespace(choices=[SimpleNamespace(message=message)])
    )
    return mock


def test_complete_uses_model_and_token_limit_from_settings():
    openai_mock = make_openai_mock()

    asyncio.run(GLMClient(openai_mock).complete(MESSAGES))

    params = openai_mock.chat.completions.create.call_args.kwargs
    assert params["model"] == settings.glm_model == "glm-5.3"
    assert params["max_tokens"] == settings.glm_max_tokens
    assert params["temperature"] == settings.glm_temperature
    assert params["messages"] == MESSAGES
    assert params["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "tools" not in params


def test_complete_passes_tools_with_auto_choice():
    openai_mock = make_openai_mock()

    asyncio.run(GLMClient(openai_mock).complete(MESSAGES, tools=TOOLS))

    params = openai_mock.chat.completions.create.call_args.kwargs
    assert params["tools"] == TOOLS
    assert params["tool_choice"] == "auto"


def test_complete_returns_first_choice_message():
    openai_mock = make_openai_mock(content='{"answer": "ok"}')

    message = asyncio.run(GLMClient(openai_mock).complete(MESSAGES))

    assert message.content == '{"answer": "ok"}'


def test_custom_token_limit_overrides_settings():
    openai_mock = make_openai_mock()

    asyncio.run(GLMClient(openai_mock, max_tokens=200).complete(MESSAGES))

    assert openai_mock.chat.completions.create.call_args.kwargs["max_tokens"] == 200


def test_timeout_raises_llm_unavailable():
    openai_mock = MagicMock()
    request = httpx.Request("POST", "https://example.test/chat/completions")
    openai_mock.chat.completions.create = AsyncMock(side_effect=APITimeoutError(request=request))

    with pytest.raises(LLMUnavailableError):
        asyncio.run(GLMClient(openai_mock).complete(MESSAGES))


def test_empty_choices_raises_llm_unavailable():
    openai_mock = MagicMock()
    openai_mock.chat.completions.create = AsyncMock(return_value=SimpleNamespace(choices=[]))

    with pytest.raises(LLMUnavailableError):
        asyncio.run(GLMClient(openai_mock).complete(MESSAGES))


def test_missing_api_key_raises_llm_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "glm_api_key", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LLMUnavailableError):
        asyncio.run(GLMClient().complete(MESSAGES))
