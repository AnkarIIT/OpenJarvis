from __future__ import annotations

import asyncio
import json
import random
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
        self._max_retries = 3
        self._base_delay = 1.0

    async def _with_retry(self, coro_factory):
        """Run an async callable with simple exponential backoff.

        Retries only on transient connection/overload style failures.
        """
        last_exc = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return await coro_factory()
            except Exception as e:  # pragma: no cover - broad catch intentional
                last_exc = e
                message = str(e).lower()
                retryable = any(
                    token in message
                    for token in [
                        "connection",
                        "timeout",
                        "temporarily",
                        "unavailable",
                        "429",
                        "503",
                        "server error",
                    ]
                )
                if not retryable or attempt == self._max_retries:
                    raise
                delay = self._base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                logger.warning(
                    "LLM call attempt %s/%s failed: %s. Retrying in %.1fs",
                    attempt,
                    self._max_retries,
                    e,
                    delay,
                )
                await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        if self.settings.llm.provider == "ollama":
            chunks = await self._with_retry(lambda: self._chat_ollama(messages, tools, stream))
            for chunk in chunks:
                yield chunk
        else:
            async for chunk in self._chat_fallback(messages, tools, stream):
                yield chunk

    async def _chat_ollama(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        stream: bool,
    ) -> list[str]:
        chunks: list[str] = []
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
                        chunks.append(chunk["message"]["content"])
                    if chunk.get("message", {}).get("tool_calls"):
                        for tool_call in chunk["message"]["tool_calls"]:
                            name = tool_call['function']['name']
                            args = tool_call['function'].get('arguments', {})
                            chunks.append(f"\n[TOOL_CALL: {name}|{json.dumps(args)}]")
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
                    chunks.append(response["message"]["content"])
                if response.get("message", {}).get("tool_calls"):
                    for tool_call in response["message"]["tool_calls"]:
                        name = tool_call['function']['name']
                        args = tool_call['function'].get('arguments', {})
                        chunks.append(f"\n[TOOL_CALL: {name}|{json.dumps(args)}]")
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            chunks.append(f"\n[Error: {str(e)}]")
        return chunks

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