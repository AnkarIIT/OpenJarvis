from __future__ import annotations

import json
import uuid
from typing import Any, AsyncGenerator

from jarvis.agent.llm_client import LLMClient
from jarvis.agent.system_prompt import get_system_prompt
from jarvis.config.settings import Settings
from jarvis.mcp.client import MCPClient
from jarvis.memory.vector_store import VectorStore
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class AgentLoop:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = LLMClient(settings)
        self.mcp = MCPClient(settings)
        self.memory = VectorStore(settings) if settings.memory.enabled else None
        self.conversation_history: list[dict[str, Any]] = []
        self.max_history = 20

    async def initialize(self) -> None:
        await self.mcp.connect_all()
        if self.memory:
            await self.memory.initialize()

    async def run(self, user_input: str, voice_mode: bool = False) -> AsyncGenerator[str, None]:
        await self._add_user_message(user_input)

        if self.memory:
            relevant_memories = await self.memory.search(user_input, limit=3)
            if relevant_memories:
                memory_context = "\n".join([f"- {m['content']}" for m in relevant_memories])
                user_input = f"[Relevant memories:\n{memory_context}]\n\n{user_input}"

        messages = self._build_messages(voice_mode)

        tool_results = []
        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            tools = await self.mcp.get_available_tools()
            tool_schemas = [self._tool_to_schema(t) for t in tools]

            full_response = ""
            tool_calls = []

            async for chunk in self.llm.chat(messages, tool_schemas, stream=True):
                if chunk.startswith("[TOOL_CALL:"):
                    tool_name = chunk[11:-1]
                    tool_calls.append(tool_name)
                else:
                    full_response += chunk
                    yield chunk

            if not tool_calls:
                await self._add_assistant_message(full_response)
                if self.memory:
                    await self.memory.add_memory(user_input, full_response)
                break

            messages.append({"role": "assistant", "content": full_response, "tool_calls": []})

            for tool_name in tool_calls:
                tool = next((t for t in tools if t.name == tool_name), None)
                if tool:
                    result = await self.mcp.call_tool(tool_name, {})
                    tool_results.append({"tool": tool_name, "result": result})
                    messages.append({
                        "role": "tool",
                        "tool_call_id": str(uuid.uuid4()),
                        "name": tool_name,
                        "content": json.dumps(result),
                    })
                    yield f"\n[Tool {tool_name} completed]\n"

    def _build_messages(self, voice_mode: bool) -> list[dict[str, Any]]:
        messages = [{"role": "system", "content": get_system_prompt(voice_mode)}]
        messages.extend(self.conversation_history[-self.max_history:])
        return messages

    def _tool_to_schema(self, tool: Any) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }

    async def _add_user_message(self, content: str) -> None:
        self.conversation_history.append({"role": "user", "content": content})

    async def _add_assistant_message(self, content: str) -> None:
        self.conversation_history.append({"role": "assistant", "content": content})

    async def get_status(self) -> dict[str, Any]:
        return {
            "model": self.settings.llm.model,
            "provider": self.settings.llm.provider,
            "mcp_connected": self.mcp.is_connected,
            "memory_enabled": self.memory is not None,
            "history_length": len(self.conversation_history),
        }