from __future__ import annotations

import json
from typing import Any, AsyncGenerator

import ollama
from pydantic import BaseModel

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class Message(BaseModel):
    role: str
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = ollama.AsyncClient(host=settings.llm.base_url)
        self.model = settings.llm.model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        if self.settings.llm.provider == "ollama":
            async for chunk in self._chat_ollama(messages, tools, stream):
                yield chunk
        else:
            async for chunk in self._chat_fallback(messages, tools, stream):
                yield chunk

    async def _chat_ollama(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        stream: bool,
    ) -> AsyncGenerator[str, None]:
        try:
            if stream:
                async for chunk in await self.client.chat(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    stream=True,
                    options={
                        "temperature": self.settings.llm.temperature,
                        "num_predict": self.settings.llm.max_tokens,
                    },
                ):
                    if chunk.get("message", {}).get("content"):
                        yield chunk["message"]["content"]
                    if chunk.get("message", {}).get("tool_calls"):
                        for tool_call in chunk["message"]["tool_calls"]:
                            yield f"\n[TOOL_CALL: {tool_call['function']['name']}]"
            else:
                response = await self.client.chat(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    stream=False,
                    options={
                        "temperature": self.settings.llm.temperature,
                        "num_predict": self.settings.llm.max_tokens,
                    },
                )
                if response.get("message", {}).get("content"):
                    yield response["message"]["content"]
                if response.get("message", {}).get("tool_calls"):
                    for tool_call in response["message"]["tool_calls"]:
                        yield f"\n[TOOL_CALL: {tool_call['function']['name']}]"

        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            yield f"\n[Error: {str(e)}]"

    async def _chat_fallback(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        stream: bool,
    ) -> AsyncGenerator[str, None]:
        yield "[Fallback: Non-Ollama providers not yet implemented]"

    async def list_models(self) -> list[str]:
        try:
            models = await self.client.list()
            return [m["name"] for m in models.get("models", [])]
        except Exception:
            return []

    async def pull_model(self, model: str) -> AsyncGenerator[str, None]:
        try:
            async for progress in await self.client.pull(model, stream=True):
                status = progress.get("status", "")
                if status:
                    yield f"{status}\n"
        except Exception as e:
            yield f"Error pulling model: {e}\n"