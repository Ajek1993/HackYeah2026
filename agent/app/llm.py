from typing import Any

from openai import OpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessage

from app.config import settings


class LLMUnavailableError(Exception):
    """GLM failed or timed out; the chat endpoint answers with "Agent chwilowo niedostępny"."""


class GLMClient:
    """Thin wrapper over the OpenAI-compatible GLM API with tool calling.

    Never logs prompts or answers — they may contain user addresses.
    """

    def __init__(
        self,
        client: OpenAI | None = None,
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> None:
        self._client = client
        self.model = model or settings.glm_model
        self.max_tokens = max_tokens or settings.glm_max_tokens
        self.temperature = settings.glm_temperature if temperature is None else temperature

    def _get_client(self) -> OpenAI:
        # Created lazily: the SDK raises when the API key is empty, which would break startup.
        if self._client is None:
            try:
                self._client = OpenAI(
                    api_key=settings.glm_api_key,
                    base_url=settings.glm_base_url,
                    timeout=settings.glm_timeout,
                    max_retries=1,
                )
            except OpenAIError as exc:
                raise LLMUnavailableError("GLM client is not configured") from exc
        return self._client

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatCompletionMessage:
        params: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            # GLM-specific parameter, not part of the OpenAI schema
            "extra_body": {"thinking": {"type": settings.glm_thinking}},
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        try:
            response = self._get_client().chat.completions.create(**params)
        except OpenAIError as exc:
            raise LLMUnavailableError("GLM request failed") from exc

        if not response.choices:
            raise LLMUnavailableError("GLM returned no choices")
        return response.choices[0].message
