from typing import Protocol

from app.core.config import settings


class ModelClient(Protocol):
    def chat(self, messages: list[dict[str, str]], model: str | None = None) -> str:
        ...

    def stream_chat(self, messages: list[dict[str, str]], model: str | None = None):
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
