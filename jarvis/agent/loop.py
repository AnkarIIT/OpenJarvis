from __future__ import annotations

import inspect
import json
import uuid
from typing import Any, AsyncGenerator

from jarvis.agent.llm_client import LLMClient
from jarvis.agent.system_prompt import get_system_prompt
from jarvis.config.settings import Settings
from jarvis.mcp.client import MCPClient
from jarvis.memory.vector_store import VectorStore
from jarvis.skills.registry import SkillRegistry
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class AgentLoop:
    def __init__(self, settings: Settings, skill_registry: SkillRegistry | None = None):
        self.settings = settings
        self.llm = LLMClient(settings)
        self.mcp = MCPClient(settings)
        self.memory = VectorStore(settings) if settings.memory.enabled else None
        self.skill_registry = skill_registry or SkillRegistry(settings)
        self.conversation_history: list[dict[str, Any]] = []
        self.max_history = 20

    async def initialize(self) -> None:
        await self.mcp.connect_all()
        if self.memory:
            await self.memory.initialize()
        await self.skill_registry.initialize()

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

            mcp_tools = await self.mcp.get_available_tools()
            skill_commands = self.skill_registry.list_commands()
            all_tools = self._merge_tools(mcp_tools, skill_commands)
            tool_schemas = [self._tool_to_schema(t) for t in all_tools]

            full_response = ""
            tool_calls = []

            async for chunk in self.llm.chat(messages, tool_schemas, stream=True):
                if chunk.startswith("[TOOL_CALL:") and chunk.endswith("]"):
                    payload = chunk[len("[TOOL_CALL: "):-1]
                    if "|" in payload:
                        tool_name, raw_args = payload.split("|", 1)
                        try:
                            tool_args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            tool_args = {}
                    else:
                        tool_name = payload
                        tool_args = {}
                    tool_calls.append((tool_name, tool_args))
                else:
                    full_response += chunk
                    yield chunk

            if not tool_calls:
                await self._add_assistant_message(full_response)
                if self.memory:
                    await self.memory.add_memory(user_input, full_response)
                break

            messages.append({"role": "assistant", "content": full_response, "tool_calls": []})

            for tool_name, tool_args in tool_calls:
                result = await self._execute_tool(tool_name, tool_args)
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

    def _merge_tools(self, mcp_tools: list[Any], skill_commands: list[Any]) -> list[Any]:
        # Keep MCP tools first; append skill commands with a simple namespace
        # to avoid collisions if an MCP tool has the same name.
        merged = list(mcp_tools)
        mcp_names = {t.name for t in merged}
        for cmd in skill_commands:
            merged.append(cmd)
        return merged

    def _tool_to_schema(self, tool: Any) -> dict[str, Any]:
        if hasattr(tool, "input_schema"):
            # MCP tool
            return {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }

        # Skill command: derive parameter schema from handler signature
        parameters = self._skill_command_schema(tool)
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": parameters,
            },
        }

    def _skill_command_schema(self, tool: Any) -> dict[str, Any]:
        handler = getattr(tool, "handler", None)
        if handler is None:
            return {"type": "object", "properties": {}}

        try:
            sig = inspect.signature(handler)
        except (ValueError, TypeError):
            return {"type": "object", "properties": {}}

        properties: dict[str, Any] = {}
        required: list[str] = []

        for name, param in sig.parameters.items():
            if name in {"self"}:
                continue
            annotation = param.annotation
            if annotation is inspect.Parameter.empty:
                json_type = "string"
            else:
                json_type = self._annotation_to_json_type(annotation)

            default = param.default if param.default is not inspect.Parameter.empty else ...
            prop: dict[str, Any] = {"type": json_type}
            if default is not ...:
                prop["default"] = default
            properties[name] = prop

            if param.default is inspect.Parameter.empty:
                required.append(name)

        schema: dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema

    @staticmethod
    def _annotation_to_json_type(annotation: Any) -> str:
        mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        # Handle typing.Optional / Union
        origin = getattr(annotation, "__origin__", None)
        args = getattr(annotation, "__args__", ())
        if origin is not None:
            # Optional[X] -> X
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                return AgentLoop._annotation_to_json_type(non_none[0])
            return "string"
        return mapping.get(annotation, "string")

    async def _execute_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        arguments = arguments or {}
        # Try MCP first
        mcp_result = await self.mcp.call_tool(tool_name, arguments)
        if "error" not in mcp_result:
            return mcp_result
        # Fall back to skill command
        try:
            return await self.skill_registry.execute_command(tool_name, **arguments)
        except TypeError:
            return await self.skill_registry.execute_command(tool_name)
        except ValueError:
            return {"error": f"Tool or skill not found: {tool_name}"}

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