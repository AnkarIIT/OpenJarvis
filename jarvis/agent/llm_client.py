from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path
from typing import Any, AsyncGenerator

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

# Provider priority order for auto-detection.
# When provider == "auto", LLMClient probes these in order and uses the first that responds.
PROVIDER_PRIORITY = [
    "ollama",
    "lm_studio",
    "localai",
    "llama_cpp",
    "openai",
    "anthropic",
]


async def _chat_ollama(
    settings: Settings,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    stream: bool,
) -> AsyncGenerator[str, None]:
    """Chat via Ollama HTTP API."""
    try:
        import ollama
    except ImportError:
        yield "[Error: ollama Python package not installed. Run: pip install ollama]"
        return
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


async def _chat_openai_compatible(
    settings: Settings,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    stream: bool,
    provider_name: str,
) -> AsyncGenerator[str, None]:
    """Chat via any OpenAI-compatible API (LM Studio, LocalAI, OpenAI).

    provider_name is used for error messages to help debugging.
    """
    try:
        import httpx
    except ImportError:
        yield f"[{provider_name} error: httpx not installed. Run: pip install httpx]"
        return

    base_url = settings.llm.base_url
    api_key = settings.llm.api_key or "not-needed"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # Convert tools to OpenAI format if present
    openai_tools = None
    if tools:
        openai_tools = []
        for t in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t.get("function", {}).get("name", ""),
                    "description": t.get("function", {}).get("description", ""),
                    "parameters": t.get("function", {}).get("parameters", {}),
                },
            })

    payload: dict[str, Any] = {
        "model": settings.llm.model,
        "messages": messages,
        "temperature": settings.llm.temperature,
        "max_tokens": settings.llm.max_tokens,
        "stream": stream,
    }
    if openai_tools:
        payload["tools"] = openai_tools

    try:
        async with httpx.AsyncClient(timeout=settings.llm.timeout or 120) as http:
            if stream:
                async with http.stream(
                    "POST",
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as resp:
                    if resp.status_code != 200:
                        text = await resp.aread()
                        yield f"[{provider_name} error: HTTP {resp.status_code} - {text.decode()[:200]}]"
                        return
                    async for line in resp.aiter_lines():
                        line = line.strip()
                        if not line or line == "data: [DONE]":
                            continue
                        if line.startswith("data: "):
                            line = line[6:]
                        try:
                            chunk_data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        choices = chunk_data.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        if delta.get("content"):
                            yield delta["content"]
                        if delta.get("tool_calls"):
                            for tc in delta["tool_calls"]:
                                fn = tc.get("function", {})
                                name = fn.get("name", "")
                                args = fn.get("arguments", "")
                                yield f"\n[TOOL_CALL: {name}|{args}"
            else:
                resp = await http.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if resp.status_code != 200:
                    yield f"[{provider_name} error: HTTP {resp.status_code} - {resp.text[:200]}]"
                    return
                data = resp.json()
                if data.get("choices"):
                    content = data["choices"][0].get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data["choices"][0].get("message", {}).get("tool_calls"):
                        for tc in data["choices"][0]["message"]["tool_calls"]:
                            fn = tc.get("function", {})
                            name = fn.get("name", "")
                            args = fn.get("arguments", {})
                            yield f"\n[TOOL_CALL: {name}|{json.dumps(args)}]"
    except Exception as e:
        logger.error(f"{provider_name} chat error: {e}")
        yield f"\n[Error: {str(e)}]"


async def _chat_anthropic(
    settings: Settings,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    stream: bool,
) -> AsyncGenerator[str, None]:
    """Chat via Anthropic Claude API."""
    try:
        import anthropic
    except ImportError:
        yield "[Anthropic error: anthropic package not installed. Run: pip install anthropic]"
        return

    api_key = settings.llm.api_key
    if not api_key:
        yield "[Anthropic error: No API key set. Configure JARVIS_LLM_API_KEY]"
        return

    client = anthropic.AsyncAnthropic(
        api_key=api_key,
        base_url=settings.llm.base_url,
    )

    # Convert tools to Anthropic format
    anthropic_tools = None
    if tools:
        anthropic_tools = []
        for t in tools:
            fn = t.get("function", {})
            anthropic_tools.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {}),
            })

    # Map OpenAI messages to Anthropic format
    anthropic_messages = []
    system_prompt = None
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            system_prompt = content
        elif role == "user":
            anthropic_messages.append({"role": "user", "content": content})
        elif role == "assistant":
            anthropic_messages.append({"role": "assistant", "content": content})
        elif role == "tool":
            # Anthropic tool results are handled differently
            anthropic_messages.append({"role": "user", "content": f"[Tool result: {content}]"})

    kwargs: dict[str, Any] = {
        "model": settings.llm.model,
        "max_tokens": settings.llm.max_tokens,
        "temperature": settings.llm.temperature,
        "messages": anthropic_messages,
    }
    if system_prompt:
        kwargs["system"] = system_prompt
    if anthropic_tools:
        kwargs["tools"] = anthropic_tools

    try:
        if stream:
            async with client.messages.stream(**kwargs) as stream_obj:
                async for content_block in stream_obj.text_stream:
                    yield content_block
        else:
            response = await client.messages.create(**kwargs)
            if response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        yield block.text
    except Exception as e:
        logger.error(f"Anthropic chat error: {e}")
        yield f"\n[Error: {str(e)}]"


async def _chat_fallback(
    settings: Settings,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    stream: bool,
) -> AsyncGenerator[str, None]:
    """Fallback that auto-detects an available provider."""
    detected = await detect_provider(settings)
    if detected == "ollama":
        async for chunk in _chat_ollama(settings, messages, tools, stream):
            yield chunk
    elif detected == "lm_studio":
        async for chunk in _chat_openai_compatible(settings, messages, tools, stream, "LM Studio"):
            yield chunk
    elif detected == "localai":
        async for chunk in _chat_openai_compatible(settings, messages, tools, stream, "LocalAI"):
            yield chunk
    elif detected == "llama_cpp":
        async for chunk in _chat_llama_cpp(settings, messages, tools, stream):
            yield chunk
    elif detected == "openai":
        async for chunk in _chat_openai_compatible(settings, messages, tools, stream, "OpenAI"):
            yield chunk
    elif detected == "anthropic":
        async for chunk in _chat_anthropic(settings, messages, tools, stream):
            yield chunk
    else:
        yield "[Error: No LLM provider available. Configure Ollama, LM Studio, LocalAI, or set an API key.]"


async def _probe_provider(settings: Settings, provider: str) -> bool:
    """Probe whether a provider is reachable and has a usable model."""
    try:
        if provider == "ollama":
            try:
                import ollama
                client = ollama.AsyncClient(host=settings.llm.base_url, timeout=5)
                tags = await asyncio.wait_for(client.list(), timeout=5.0)
                model_names = [m.get("name", "") for m in tags.get("models", [])]
                if model_names:
                    # Try to use the configured model, or fall back to first available
                    if settings.llm.model not in model_names:
                        settings.llm.model = model_names[0]
                    return True
                return False
            except Exception:
                return False

        elif provider in ("lm_studio", "localai", "openai"):
            import httpx
            base = settings.llm.base_url
            if provider == "openai":
                base = base or "https://api.openai.com/v1"
            async with httpx.AsyncClient(timeout=5) as http:
                # Check models endpoint
                headers = {}
                if settings.llm.api_key:
                    headers["Authorization"] = f"Bearer {settings.llm.api_key}"
                resp = await http.get(f"{base.rstrip('/')}/v1/models", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("data", [])
                    if models:
                        # Pick the first model if configured model not found
                        model_ids = [m.get("id", "") for m in models]
                        if settings.llm.model not in model_ids:
                            settings.llm.model = model_ids[0]
                        return True
                return False

        elif provider == "anthropic":
            if not settings.llm.api_key:
                return False
            import httpx
            async with httpx.AsyncClient(timeout=5) as http:
                resp = await http.get(
                    "https://api.anthropic.com/v1/models",
                    headers={"x-api-key": settings.llm.api_key},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("data", [])
                    if models and not settings.llm.model:
                        settings.llm.model = models[0].get("id", "claude-3-5-sonnet-20241022")
                    return True
                return False

        elif provider == "llama_cpp":
            from llama_cpp import Llama
            model_path = settings.llm.model_path
            if model_path and Path(model_path).exists():
                return True
            # Scan common directories for .gguf files
            candidates = [
                Path.home() / ".lmstudio/models",
                Path.home() / ".local/share/llm_models",
                Path.home() / "models",
                Path.cwd() / "models",
            ]
            for c in candidates:
                if c.exists():
                    gguf_files = list(c.rglob("*.gguf"))
                    if gguf_files:
                        settings.llm.model_path = str(gguf_files[0])
                        return True
            return False

    except Exception:
        return False

    return False


async def detect_provider(settings: Settings, provider: str | None = None) -> str | None:
    """Detect the best available LLM provider.

    If *provider* is given and not "auto", probe just that one.
    If provider is "auto" or None, probe providers in provider priority order.
    Returns the provider name of the first reachable one, or None.
    """
    if provider and provider != "auto":
        if await _probe_provider(settings, provider):
            logger.info(f"LLM provider '{provider}' is available")
            return provider
        return None

    # Auto-detect: probe in priority order
    for p in PROVIDER_PRIORITY:
        # Skip if provider requires deps we know are missing
        base_url = settings.llm.base_url
        if p == "ollama":
            # Ollama typically runs at localhost:11434
            if "localhost" not in base_url and "127.0.0.1" not in base_url:
                # User set a different base_url; respect it
                pass
        if await _probe_provider(settings, p):
            logger.info(f"Auto-detected LLM provider: {p} (model: {settings.llm.model})")
            settings.llm.provider = p  # Persist the decision
            return p

    return None


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.llm.model
        self._max_retries = 3
        self._base_delay = 1.0
        self._detected_provider: str | None = None

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

    def _resolve_provider(self) -> str:
        """Resolve the effective provider, auto-detecting if needed."""
        provider = self.settings.llm.provider

        if provider == "auto":
            if self._detected_provider is None:
                # Run detection synchronously via asyncio (safe in async context)
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                async def _detect():
                    nonlocal detected
                    detected = await detect_provider(self.settings)
                    return detected

                detected: str | None = None
                if loop.is_running():
                    # We're inside an async context; schedule detection
                    # and fall back to the configured provider
                    detected = None
                else:
                    detected = loop.run_until_complete(detect_provider(self.settings))

                if detected:
                    self._detected_provider = detected
                    provider = detected
                else:
                    # No provider detected — fall back to configured or default
                    provider = "ollama"
                    logger.warning("No LLM provider auto-detected; falling back to Ollama")
            else:
                provider = self._detected_provider
        elif self._detected_provider:
            provider = self._detected_provider

        return provider

    async def _detect_or_resolve(self) -> str:
        """Async provider resolution for use inside coroutines."""
        provider = self.settings.llm.provider

        if provider == "auto" or self._detected_provider:
            detected = await detect_provider(self.settings, provider if provider != "auto" else None)
            if detected:
                self._detected_provider = detected
                return detected
            if provider != "auto":
                return provider  # User specified a provider; try it even if probe fails
            # Auto mode and nothing detected
            logger.warning("No LLM provider auto-detected; falling back to Ollama")
            return "ollama"

        return provider

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        # Resolve provider (with auto-detection)
        provider = await self._detect_or_resolve()
        logger.debug(f"LLM provider resolved: {provider}")

        # Prefer smaller models for lower latency if configured
        if provider == "ollama" and self.settings.llm.model and ":" in self.settings.llm.model:
            model_name = self.settings.llm.model
            large_models = ["13b", "70b", "7b"]
            if any(size in model_name for size in large_models):
                logger.info(f"Model {model_name} may have high latency. Consider smaller models.")

        provider_handlers = {
            "ollama": _chat_ollama,
            "lm_studio": lambda s, m, t, st: _chat_openai_compatible(s, m, t, st, "LM Studio"),
            "localai": lambda s, m, t, st: _chat_openai_compatible(s, m, t, st, "LocalAI"),
            "openai": lambda s, m, t, st: _chat_openai_compatible(s, m, t, st, "OpenAI"),
            "anthropic": _chat_anthropic,
            "llama_cpp": _chat_llama_cpp,
        }

        handler = provider_handlers.get(provider)
        if handler:
            # Determine if we can fall back (auto-detected provider)
            was_auto = self.settings.llm.provider in ("auto",) and provider != self.settings.llm.provider

            try:
                async for chunk in self._with_retry_generator(
                    lambda: handler(self.settings, messages, tools, stream)
                ):
                    yield chunk
            except Exception as e:
                if was_auto:
                    # Auto-detected provider failed — try fallback
                    logger.error(f"LLM provider {provider} failed: {e}")
                    async for chunk in _chat_fallback(self.settings, messages, tools, stream):
                        yield chunk
                else:
                    # Explicit provider — re-raise so caller gets the error
                    raise
        else:
            async for chunk in _chat_fallback(self.settings, messages, tools, stream):
                yield chunk

    @property
    def provider_name(self) -> str:
        """Get the resolved provider name for display purposes."""
        return self._detected_provider or self.settings.llm.provider

    async def list_models(self) -> list[str]:
        provider = self.settings.llm.provider
        if provider in ("auto",):
            provider = self._detected_provider or "ollama"

        if provider == "ollama":
            try:
                import ollama
                client = ollama.AsyncClient(host=self.settings.llm.base_url)
                models = await client.list()
                return [m["name"] for m in models.get("models", [])]
            except Exception:
                return []
        elif provider in ("lm_studio", "localai", "openai"):
            import httpx
            base = self.settings.llm.base_url
            if provider == "openai":
                base = base or "https://api.openai.com/v1"
            headers = {}
            if self.settings.llm.api_key:
                headers["Authorization"] = f"Bearer {self.settings.llm.api_key}"
            try:
                async with httpx.AsyncClient(timeout=10) as http:
                    resp = await http.get(f"{base.rstrip('/')}/v1/models", headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        return [m["id"] for m in data.get("data", [])]
            except Exception:
                return []
            return []
        elif provider == "anthropic":
            try:
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=self.settings.llm.api_key)
                models = await client.models.list()
                return [m.id for m in models.data]
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
        """Pull model — Ollama pulls from registry, llama_cpp downloads GGUF,
        LM Studio/LocalAI/OpenAI skip (managed externally)."""
        provider = self.settings.llm.provider
        if provider in ("auto",):
            provider = self._detected_provider or "ollama"

        if provider == "ollama":
            try:
                import ollama
                client = ollama.AsyncClient(host=self.settings.llm.base_url)
                async for progress in await client.pull(model, stream=True):
                    status = progress.get("status", "")
                    if status:
                        yield f"{status}\n"
            except Exception as e:
                yield f"Error pulling model: {e}\n"
        elif provider == "llama_cpp":
            if not model.startswith("http"):
                yield f"For llama_cpp, provide a direct GGUF URL or local path\n"
                return

            # Download GGUF model
            model_path = Path.home() / ".jarvis" / "models" / model.split("/")[-1]
            model_path.parent.mkdir(parents=True, exist_ok=True)

            yield f"Downloading {model.split('/')[-1]}...\n"
            try:
                import urllib.request
                urllib.request.urlretrieve(model, str(model_path))
                self.settings.llm.model_path = str(model_path)
                yield f"Downloaded to {model_path}\n"
            except Exception as e:
                yield f"Download failed: {e}\n"
        elif provider in ("lm_studio", "localai"):
            yield f"{provider} manages models via its own UI. Use {provider} to download '{model}'.\n"
        elif provider == "openai":
            yield f"OpenAI models are managed via the API. '{model}' is available at api.openai.com.\n"
        else:
            yield f"Model pulling not supported for provider '{provider}'\n"
