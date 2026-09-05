from __future__ import annotations

import asyncio
import json
import random
from typing import Any, AsyncGenerator

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


async def _chat_ollama(
    settings: Settings,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    stream: bool,
) -> AsyncGenerator[str, None]:
    """Chat via Ollama HTTP API."""
    import ollama
    client = ollama.AsyncClient(host=settings.llm.base_url)

    try:
        if stream:
            async for chunk in await client.chat(
                model=settings.llm.model,
                messages=messages,
                tools=tools,
                stream=True,
                options={
                    "temperature": settings.llm.temperature,
                    "num_predict": settings.llm.max_tokens,
                },
            ):
                if chunk.get("message", {}).get("content"):
                    yield chunk["message"]["content"]
                if chunk.get("message", {}).get("tool_calls"):
                    for tool_call in chunk["message"]["tool_calls"]:
                        name = tool_call["function"]["name"]
                        args = tool_call["function"].get("arguments", {})
                        yield f"\n[TOOL_CALL: {name}|{json.dumps(args)}]"
        else:
            response = await client.chat(
                model=settings.llm.model,
                messages=messages,
                tools=tools,
                stream=False,
                options={
                    "temperature": settings.llm.temperature,
                    "num_predict": settings.llm.max_tokens,
                },
            )
            if response.get("message", {}).get("content"):
                yield response["message"]["content"]
            if response.get("message", {}).get("tool_calls"):
                for tool_call in response["message"]["tool_calls"]:
                    name = tool_call["function"]["name"]
                    args = tool_call["function"].get("arguments", {})
                    yield f"\n[TOOL_CALL: {name}|{json.dumps(args)}]"
    except Exception as e:
        logger.error(f"Ollama chat error: {e}")
        yield f"\n[Error: {str(e)}]"


async def _chat_llama_cpp(
    settings: Settings,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    stream: bool,
) -> AsyncGenerator[str, None]:
    """Chat via llama-cpp-python (direct GGUF model inference)."""
    try:
        from llama_cpp import Llama
    except ImportError:
        yield "[Error: llama-cpp-python not installed. Run: pip install llama-cpp-python]"
        return

    # Resolve model path
    model_path = settings.llm.model_path or settings.llm.model
    if not model_path:
        yield "[Error: No GGUF model path set. Configure JARVIS_LLM_MODEL_PATH]"
        return

    # Cache model instance on settings to avoid reloading
    if not hasattr(settings.llm, "_llama_instance") or settings.llm._llama_instance is None:
        logger.info(f"Loading llama.cpp model: {model_path}")
        settings.llm._llama_instance = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_batch=512,
            n_gpu_layers=0,
            verbose=False,
        )

    prompt = _messages_to_prompt(messages, tools)

    if stream:
        for chunk in settings.llm._llama_instance(
            prompt,
            max_tokens=settings.llm.max_tokens,
            temperature=settings.llm.temperature,
            stop=["</s>", "[INST]", "[/INST]"],
            stream=True,
        ):
            text = chunk["choices"][0]["text"]
            if text:
                yield text
    else:
        result = settings.llm._llama_instance(
            prompt,
            max_tokens=settings.llm.max_tokens,
            temperature=settings.llm.temperature,
            stop=["</s>", "[INST]", "[/INST]"],
            stream=False,
        )
        text = result["choices"][0]["text"]
        if text:
            yield text


def _messages_to_prompt(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None) -> str:
    """Convert OpenAI-format messages to a llama.cpp compatible prompt."""
    prompt = ""
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            prompt += f"[INST] <<SYS>>\n{content}\n<</SYS>>\n\n"
        elif role == "user":
            prompt += f"[INST] {content} [/INST] "
        elif role == "assistant":
            prompt += f"{content} "
        elif role == "tool":
            prompt += f"[Tool result: {content}] "
    if tools:
        tool_names = ", ".join(t.get("function", {}).get("name", "unknown") for t in tools)
        prompt += f"\n[Available tools: {tool_names}]"
    return prompt.strip()


async def _chat_fallback(
    settings: Settings,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    stream: bool,
) -> AsyncGenerator[str, None]:
    """Fallback for providers without direct implementation."""
    provider = settings.llm.provider
    if provider == "openai":
        yield "[OpenAI fallback: Install openai package or use Ollama]"
    elif provider == "anthropic":
        yield "[Anthropic fallback: Install anthropic package or use Ollama]"
    else:
        yield f"[Unsupported LLM provider: {provider}. Set provider to 'ollama' or 'llama_cpp'.]"


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.llm.model
        self._max_retries = 3
        self._base_delay = 1.0

    async def _with_retry_generator(self, gen_factory):
        """Retry an async generator factory on transient failures.

        Restarts the generator from scratch on retryable errors.
        """
        last_exc = None
        for attempt in range(1, self._max_retries + 1):
            try:
                async for chunk in gen_factory():
                    yield chunk
                return
            except Exception as e:
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
                    "LLM attempt %s/%s failed: %s. Retrying in %.1fs",
                    attempt,
                    self._max_retries,
                    e,
                    delay,
                )
                await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]

    async def _with_retry(self, coro_factory):
        """Run an async callable with simple exponential backoff.

        Retries only on transient connection/overload style failures.
        """
        last_exc = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return await coro_factory()
            except Exception as e:
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
        provider = self.settings.llm.provider

        if provider == "ollama":
            async for chunk in self._with_retry_generator(
                lambda: _chat_ollama(self.settings, messages, tools, stream)
            ):
                yield chunk
        elif provider == "llama_cpp":
            async for chunk in self._with_retry_generator(
                lambda: _chat_llama_cpp(self.settings, messages, tools, stream)
            ):
                yield chunk
        else:
            async for chunk in _chat_fallback(self.settings, messages, tools, stream):
                yield chunk

    async def list_models(self) -> list[str]:
        provider = self.settings.llm.provider
        if provider == "ollama":
            try:
                import ollama
                client = ollama.AsyncClient(host=self.settings.llm.base_url)
                models = await client.list()
                return [m["name"] for m in models.get("models", [])]
            except Exception:
                return []
        elif provider == "llama_cpp":
            # List .gguf files in common model directories
            model_path = self.settings.llm.model_path
            if model_path and Path(model_path).exists():
                return [model_path]
            # Try common directories
            candidates = [
                Path.home() / ".lmstudio/models",
                Path.home() / ".local/share/llm_models",
                Path.home() / "models",
                Path.cwd() / "models",
            ]
            found = []
            for c in candidates:
                if c.exists():
                    for f in c.rglob("*.gguf"):
                        found.append(str(f))
            return found
        return []

    async def pull_model(self, model: str) -> AsyncGenerator[str, None]:
        """Pull model — Ollama pulls from registry, llama_cpp downloads GGUF."""
        if self.settings.llm.provider == "ollama":
            try:
                import ollama
                client = ollama.AsyncClient(host=self.settings.llm.base_url)
                async for progress in await client.pull(model, stream=True):
                    status = progress.get("status", "")
                    if status:
                        yield f"{status}\n"
            except Exception as e:
                yield f"Error pulling model: {e}\n"
        elif self.settings.llm.provider == "llama_cpp":
            from pathlib import Path
            import urllib.request

            if not model.startswith("http"):
                yield f"For llama_cpp, provide a direct GGUF URL or local path\n"
                return

            # Download GGUF model
            model_path = Path.home() / ".jarvis" / "models" / model.split("/")[-1]
            model_path.parent.mkdir(parents=True, exist_ok=True)

            yield f"Downloading {model.split('/')[-1]}...\n"
            try:
                urllib.request.urlretrieve(model, str(model_path))
                self.settings.llm.model_path = str(model_path)
                yield f"Downloaded to {model_path}\n"
            except Exception as e:
                yield f"Download failed: {e}\n"
