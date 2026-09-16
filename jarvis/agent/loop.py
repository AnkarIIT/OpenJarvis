from __future__ import annotations

import inspect
import json
import asyncio
from typing import Any, AsyncGenerator, Awaitable, Callable

from jarvis.agent.llm_client import LLMClient
from jarvis.agent.system_prompt import get_system_prompt
from jarvis.config.settings import Settings
from jarvis.mcp.client import MCPClient
from jarvis.memory.vector_store import VectorStore
from jarvis.agent.permissions import (
    action_policy,
    confirmation_required_result,
    requires_confirmation,
)
from jarvis.agent.tasks import AgentTask, TaskStore
from jarvis.agent.audit import AuditLogger
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
        self.current_task: AgentTask | None = None
        self.last_task: AgentTask | None = None
        self.task_store = TaskStore(self.settings.task_state_file)
        self.last_task = self.task_store.latest()
        self.audit = AuditLogger(self.settings.mcp.audit_file)
        self.approval_handler: Callable[
            [str, str, dict[str, Any]], Awaitable[bool]
        ] | None = None

    @property
    def vector_store(self) -> VectorStore | None:
        """Convenience alias for self.memory (VectorStore)."""
        return self.memory

    async def initialize(self) -> None:
        await self.mcp.connect_all()
        if self.memory:
            await self.memory.initialize()
        await self.skill_registry.initialize()

    async def run(self, user_input: str, voice_mode: bool = False) -> AsyncGenerator[str, None]:
        task = AgentTask()
        task.start()
        self.task_store.save(task)
        self.current_task = task
        try:
            async for chunk in self._run(user_input, voice_mode):
                yield chunk
        except asyncio.CancelledError:
            task.finish("cancelled")
            raise
        except Exception as exc:
            task.finish("failed", str(exc))
            raise
        else:
            task.finish("completed")
        finally:
            self.last_task = task
            self.current_task = None
            self.task_store.save(task)

    async def _run(self, user_input: str, voice_mode: bool = False) -> AsyncGenerator[str, None]:
        if self.current_task:
            self.current_task.add_step("plan", "Analyze request and select tools")
            self.task_store.save(self.current_task)
        await self._add_user_message(user_input)

        original_input = user_input
        if self.memory:
            relevant_memories = await self.memory.search(original_input, limit=3)
            if relevant_memories:
                memory_context = "\n".join([f"- {m['content']}" for m in relevant_memories])
                user_input = f"[Relevant memories:\n{memory_context}]\n\n{user_input}"

        messages = self._build_messages(voice_mode)
        if user_input != original_input:
            messages[-1] = {"role": "user", "content": user_input}

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
                if isinstance(chunk, dict) and chunk.get("type") == "tool_call":
                    tool_calls.append(chunk)
                elif isinstance(chunk, str) and chunk.startswith("[TOOL_CALL:") and chunk.endswith("]"):
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
                    tool_calls.append({
                        "id": str(len(tool_calls)),
                        "name": tool_name,
                        "arguments": tool_args,
                    })
                else:
                    full_response += chunk
                    yield chunk

            if not tool_calls:
                await self._add_assistant_message(full_response)
                if self.memory:
                    await self.memory.add_memory(user_input, full_response)
                break

            messages.append({
                "role": "assistant",
                "content": full_response or None,
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call.get("arguments", {})),
                        },
                    }
                    for call in tool_calls
                ],
            })

            for call in tool_calls:
                tool_name = call["name"]
                tool_args = call.get("arguments", {})
                if self.current_task:
                    self.current_task.add_step("execute", f"Run tool {tool_name}", "running")
                result = await self._execute_tool(tool_name, tool_args)
                if self.current_task:
                    step_status = "failed" if isinstance(result, dict) and result.get("error") else "completed"
                    self.current_task.add_step(
                        "verify",
                        f"Verify result from {tool_name}",
                        step_status,
                    )
                    self.task_store.save(self.current_task)
                tool_results.append({"tool": tool_name, "result": result})
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result),
                })
                yield f"\n[Tool {tool_name} completed]\n"

    def _build_messages(self, voice_mode: bool) -> list[dict[str, Any]]:
        messages = [{
            "role": "system",
            "content": get_system_prompt(
                voice_mode,
                language=self.settings.voice.language,
                language_detection=self.settings.voice.language_detection,
            ),
        }]
        messages.extend(self.conversation_history[-self.max_history:])
        return messages

    def _merge_tools(self, mcp_tools: list[Any], skill_commands: list[Any]) -> list[Any]:
        # Keep MCP tools first; append skill commands that don't collide with MCP tool names.
        merged = list(mcp_tools)
        mcp_names = {t.name for t in merged}
        for cmd in skill_commands:
            if cmd.name in mcp_names:
                logger.warning(f"Skill command '{cmd.name}' skipped (collides with MCP tool)")
                continue
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
        # Check which tool source has this tool name first (avoids MCP timeout for local skills)
        mcp_tool = next((t for t in self.mcp.tools if t.name == tool_name), None)
        skill_cmd = next((c for c in self.skill_registry.list_commands() if c.name == tool_name), None)

        if mcp_tool:
            source = f"mcp:{mcp_tool.server_name}"
            self._audit_tool(tool_name, source, "requested", arguments)
            policy = action_policy(self.settings, mcp_tool.server_name, tool_name)
            if policy == "deny":
                blocked = confirmation_required_result(tool_name, mcp_tool.server_name)
                blocked["message"] = (
                    f"Tool '{tool_name}' is denied by the configured policy and was not executed."
                )
                self._audit_tool(tool_name, source, "denied", arguments, blocked["message"])
                return blocked
            if requires_confirmation(self.settings, mcp_tool.server_name, tool_name):
                approved = False
                if self.approval_handler is not None:
                    approved = await self.approval_handler(
                        tool_name,
                        mcp_tool.server_name,
                        arguments,
                    )
                if approved:
                    self._audit_tool(tool_name, source, "approved", arguments)
                else:
                    blocked = confirmation_required_result(tool_name, mcp_tool.server_name)
                    self._audit_tool(tool_name, source, "blocked", arguments, blocked["message"])
                    return blocked
            result = await self.mcp.call_tool(tool_name, arguments)
            if "error" in result:
                self._audit_tool(tool_name, source, "failed", arguments, str(result["error"]))
                return {"error": result["error"]}
            self._audit_tool(tool_name, source, "completed", arguments)
            return result
        elif skill_cmd:
            source = "skill"
            self._audit_tool(tool_name, source, "requested", arguments)
            try:
                result = await self.skill_registry.execute_command(tool_name, **arguments)
            except TypeError:
                result = await self.skill_registry.execute_command(tool_name)
            self._audit_tool(tool_name, source, "completed", arguments)
            return result
        self._audit_tool(tool_name, "unknown", "failed", arguments, "tool not found")
        return {"error": f"Tool or skill not found: {tool_name}"}

    def _audit_tool(
        self,
        tool_name: str,
        source: str,
        status: str,
        arguments: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        if self.settings.mcp.audit_enabled:
            self.audit.record(
                task_id=self.current_task.task_id if self.current_task else None,
                tool=tool_name,
                source=source,
                status=status,
                arguments=arguments,
                error=error,
            )

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
            "current_task": self.current_task.as_dict() if self.current_task else None,
            "last_task": self.last_task.as_dict() if self.last_task else None,
        }