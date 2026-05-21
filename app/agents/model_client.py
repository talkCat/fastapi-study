import json
from typing import Any, Protocol

from app.core.config import settings


class ModelClient(Protocol):
    def chat(self, messages: list[dict[str, str]], model: str | None = None) -> str:
        ...

    def stream_chat(self, messages: list[dict[str, str]], model: str | None = None):
        ...

    def plan(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        model: str | None = None,
    ) -> dict[str, Any]:
        ...


class OpenAICompatibleChatClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or settings.openai_api_key
        self.base_url = base_url if base_url is not None else settings.openai_base_url
        self.model = model or settings.openai_model

    def chat(self, messages: list[dict[str, str]], model: str | None = None) -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for the chat agent")

        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url or None)
        response = client.chat.completions.create(
            model=model or self.model,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    def plan(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        model: str | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for the chat agent")

        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url or None)
        response = client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        choice = response.choices[0]
        message = choice.message
        tool_calls = []
        for item in getattr(message, "tool_calls", None) or []:
            function = getattr(item, "function", None)
            raw_arguments = getattr(function, "arguments", "") if function else ""
            parsed_arguments = _parse_tool_arguments(raw_arguments)
            tool_calls.append(
                {
                    "id": getattr(item, "id", None),
                    "type": getattr(item, "type", "function"),
                    "name": getattr(function, "name", None) if function else None,
                    "arguments": parsed_arguments,
                    "raw_arguments": raw_arguments,
                }
            )
        return {
            "content": message.content or "",
            "tool_calls": tool_calls,
            "finish_reason": getattr(choice, "finish_reason", None),
        }

    def stream_chat(self, messages: list[dict[str, str]], model: str | None = None):
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for the chat agent")

        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url or None)
        stream = client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content


def _parse_tool_arguments(raw_arguments: str) -> dict[str, Any]:
    text = (raw_arguments or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Tool arguments are not valid JSON: {text}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Tool arguments must decode to a JSON object")
    return parsed
