# JARVIS Project Analysis — Skills, Capabilities, Flaws, and Flow

> Status: based on codebase at `C:\codes\jarvis` after external-skill integration and critical fixes.
> Last updated: 2026-09-04

---

## 1. Skills Inventory

### 1.1 Built-in Skills (4 skills, 15 commands)

| Skill | Commands | Description |
|-------|----------|-------------|
| `system_monitor` | 6 | CPU, memory, disk, GPU, top processes, overall status |
| `code_assistant` | 3 | AST-based analyze_code, find_todos, list_functions |
| `memory` | 3 | remember, recall, forget via VectorStore |
| `voice_control` | 3 | voice_on/off/test with pipeline injection |

### 1.2 External / Wrapper Skills (6 skills, 29 commands)

| Skill | Commands | Description |
|-------|----------|-------------|
| `marketing` | 3 | List/read 11 playbooks, check status |
| `visualizer` | 6 | Start/stop server, set state/face, demo mode, status |
| `memory_vault` | 6 | Init/status/list/read/write/prime Obsidian vault |
| `barehands` | 6 | Start/stop board server, stage cards, present, ring state |
| `backtalk` | 6 | Start/stop voice loop, set state/mood, config, status |
| `fullstack_agent` | 4 | Status, update, launchers, setup wizard |

**Total: 10 skills, 46 commands.**

---

## 2. What JARVIS Can Do

### 2.1 Chat / Agent Core
- **Terminal UI** via Textual (`ChatScreen`, `SkillsScreen`, `ToolsScreen`, `MemoryScreen`, `VoiceScreen`, `SettingsScreen`)
- **Local LLM** via Ollama (default `llama3.1:8b`); supports streaming responses
- **Tool calling**: LLM can invoke MCP tools and skill commands as function calls
- **Conversation history**: last 20 messages kept in memory
- **Memory injection**: searches ChromaDB for relevant memories and prepends them to the prompt
- **Command palette** (`Ctrl+K`) and keyboard shortcuts for all screens

### 2.2 Voice Pipeline
- **Wake word**: "Hey JARVIS" via Porcupine/Vosk wake-word detector
- **STT**: Vosk offline speech-to-text
- **TTS**: Piper offline text-to-speech
- **Push-to-talk**: `Ctrl+Space`
- **Voice mode**: agent runs with `voice_mode=True`, speaks last assistant response

### 2.3 MCP Servers (5 servers, bundled)
- **Filesystem**: read/write/list/glob files (sandboxed to root)
- **Terminal**: run allowed shell commands + background processes
- **Git**: status, diff, log, branch, add, commit
- **Memory**: ChromaDB-backed add/search/list/delete memories via MCP
- **Web search**: DuckDuckGo HTML search + URL fetch (with optional API key)

### 2.4 External Integrations (subprocess/HTTP/file orchestration)
- **Marketing**: reads `ai-marketing-skills/jaredrhod-marketing/*.md` playbooks
- **Visualizer**: controls `ai-visualizer` HTTP server, writes signal-bus files
- **Memory Vault**: reads/writes Obsidian vault markdown files
- **Barehands**: controls `barehands` server via HTTP POST, stages cards/media
- **Backtalk**: starts/stops `backtalk` voice loop subprocess, manages ring state
- **Fullstack Agent**: status checks, update scripts, Desktop launcher creation

### 2.5 Installation / Setup
- **One-command installer** (`jarvis --install`):
  - Detects Python version, RAM, CPU
  - Detects/installs Ollama
  - Pulls recommended model based on RAM
  - Downloads voice models (Piper + Vosk)
  - Configures MCP servers
  - Writes `~/.jarvis/config.json`
  - Adds to PATH

### 2.6 Skills Management (TUI)
- `Ctrl+G` opens Skills screen
- Lists all discovered skills with enabled/disabled status
- Enter toggles skill enabled state via `SkillRegistry`
- Refresh reloads from disk

---

## 3. Flaws, Gaps, and Blockers

### 3.1 Critical / Blocking

| # | Flaw | Impact | Location |
|---|------|--------|----------|
| 1 | **Circular import in `mcp/__init__.py`** | Full package import fails; `python -m jarvis.main` and TUI launch are broken out-of-the-box | `jarvis/mcp/__init__.py` → `jarvis.mcp.client` → `mcp` package → `jarvis/mcp/__init__.py` |
| 2 | **Code-assistant commands are stubs** | `analyze_code`, `find_todos`, `list_functions` return placeholder strings | `jarvis/skills/builtin/code_assistant.py` |
| 3 | **Voice control commands are stubs** | `voice_on`, `voice_off`, `voice_test` don't touch real voice pipeline | `jarvis/skills/builtin/voice_control.py` |
| 4 | **Memory skill is a stub** | `remember`, `recall`, `forget` don't call `VectorStore` | `jarvis/skills/builtin/memory.py` |

### 3.2 High / Functional Gaps

| # | Flaw | Impact |
|---|------|--------|
| 5 | **Sentence-transformers optional dependency missing** | Semantic memory search silently disabled if `nomic-embed-text` model isn't cached; falls back to no embeddings | `jarvis/memory/vector_store.py` |
| 6 | **Skill command argument schema is weak** | LLM tool schema exposes no parameters for skill commands (`properties: {}`); argument passing works only when LLM guesses keyword names correctly | `jarvis/agent/loop.py` `_tool_to_schema` |
| 7 | **MCP server executables don't exist** | Installer configures `jarvis-mcp-filesystem`, `jarvis-mcp-terminal`, etc., but no entry points are defined in `pyproject.toml`; MCP servers won't launch | `jarvis/config/installer.py` + `pyproject.toml` |
| 8 | **TUI cannot fully launch due to circular import** | Even after fixing circular import, `JarvisApp.run()` requires a real terminal; smoke-testing in headless environments is hard | `jarvis/tui/app.py` |
| 9 | **No error recovery for failed MCP connections** | If an MCP server fails to start, the agent loop continues but tools silently disappear | `jarvis/mcp/client.py` |
| 10 | **`backtalk` and `fullstack_agent` path resolution untested at runtime** | Path resolution uses `settings.external_*_dir` but those repos may not be present; commands return path-not-found strings | `jarvis/skills/external/backtalk/skill.py`, `fullstack_agent/skill.py` |

### 3.3 Medium / Design Concerns

| # | Flaw | Impact |
|---|------|--------|
| 11 | **Mixed tool namespaces (MCP vs skill commands)** | Collisions possible if an MCP tool and skill command share a name; current code dedupes by MCP-first but doesn't warn | `jarvis/agent/loop.py` `_merge_tools` |
| 12 | **`_execute_tool` swallows `TypeError` silently** | If a skill command signature rejects kwargs, it falls back to no-arg call without logging the mismatch | `jarvis/agent/loop.py` |
| 13 | **`llm_client.py` tool-call serialization is fragile** | Arguments are JSON-serialized into a string chunk (`[TOOL_CALL: name|{...}]`); complex nested args may break parsing | `jarvis/agent/llm_client.py` |
| 14 | **Voice pipeline doesn't handle TTS errors** | `speak` and `speak_last_response` ignore failures; user gets no feedback if Piper fails | `jarvis/voice/pipeline.py` |
| 15 | **`barehands` and `backtalk` share state-dir pattern** | Both write to `<repo>/state/` with `state`, `mood.json`, `wave.json`; if both run concurrently they can clobber each other's state | `jarvis/skills/external/barehands/skill.py`, `backtalk/skill.py` |
| 16 | **No tests for external skills** | Only `tests/test_settings.py` exists; 29 new commands have zero unit coverage | `tests/` |
| 17 | **Skills screen toggle doesn't persist** | `enable_skill`/`disable_skill` updates in-memory `settings.skills.enabled` but never calls `save_settings` | `jarvis/skills/registry.py` + `jarvis/tui/screens/skills.py` |
| 18 | **`memory_vault` and `visualizer` state dirs not created automatically** | `memory_vault_init` creates vault structure but `visualizer_start` assumes `~/.jarvis/visualizer_bus/` exists | `jarvis/skills/external/visualizer/skill.py`, `memory_vault/skill.py` |

---

## 4. End-to-End Flow

### 4.1 Startup Flow

```
jarvis main()
  └─> load_settings()
       └─> Settings() reads ~/.jarvis/.env + defaults
  └─> setup_file_logging()
  └─> JarvisApp(settings)
       ├─> SkillRegistry(settings)
       │    └─> SkillLoader.discover_skills()
       │         ├─> scans skills_paths for SKILL.md / skill.yaml
       │         └─> registers builtin + external skills
       └─> AgentLoop(settings, skill_registry)
            ├─> LLMClient(settings)
            ├─> MCPClient(settings)
            └─> VectorStore(settings)  [if memory enabled]
  └─> app.run()
       └─> on_mount()
            ├─> switch_screen("chat")
            └─> voice_pipeline.start_wake_word_listener()  [if enabled]
```

### 4.2 Chat / Tool-Call Flow

```
User types message
  └─> ChatScreen._send_message()
       ├─> chat_panel.add_user_message()
       └─> agent_loop.run(message)
            ├─> _add_user_message() → history
            ├─> memory.search() → inject relevant memories
            ├─> _build_messages() → system + history
            └─> while iterations < max:
                 ├─> mcp.get_available_tools() + skill_registry.list_commands()
                 ├─> _merge_tools() → MCP tools + skill commands
                 ├─> _tool_to_schema() → OpenAI function schema per tool
                 ├─> llm.chat(messages, tool_schemas, stream=True)
                 │    └─> Ollama returns chunks + tool_calls
                 │         └─> yields "[TOOL_CALL: name|{args}]"
                 ├─> parse tool name + JSON args from chunks
                 ├─> if tool_calls:
                 │    ├─> _execute_tool(name, args)
                 │    │    ├─> mcp.call_tool(name, args)
                 │    │    └─> fallback: skill_registry.execute_command(name, **args)
                 │    ├─> append tool result to messages
                 │    └─> yield "[Tool X completed]"
                 └─> else: final assistant text → save to memory
```

### 4.3 Voice Flow

```
Wake word detected ("Hey JARVIS")
  └─> VoicePipeline._on_wake_word()
       ├─> start_listening()
       └─> _process_voice_command()
            ├─> stt.listen_once(timeout=10s)
            ├─> agent_loop.run(text, voice_mode=True)
            │    └─> (same tool-call loop as chat)
            └─> speak_last_response()
                 └─> tts.speak(last assistant message)
```

### 4.4 Skills Toggle Flow

```
Ctrl+G → SkillsScreen
  └─> _load_skills()
       ├─> skill_registry.loader.discover_skills()
       └─> populate ListView with enabled/disabled status
  └─> Enter on selected skill
       └─> action_toggle_skill()
            ├─> skill_registry.enable/disable_skill(name)
            └─> refresh list view
```

### 4.5 External Skill Subprocess Flow (example: `backtalk`)

```
User: "start backtalk"
  └─> LLM calls backtalk_start
       └─> _execute_tool("backtalk_start", {})
            └─> skill_registry.execute_command("backtalk_start")
                 └─> BacktalkSkill._start()
                      ├─> resolves backtalk_dir / state_dir from settings
                      ├─> creates subprocess: python backtalk/backtalk/main.py
                      └─> returns PID
  └─> User: "set ring to listening"
       └─> LLM calls backtalk_set_state with state="listening"
            └─> BacktalkSkill._set_state("listening")
                 └─> writes "listening" → backtalk/state/state
```

---

## 5. Summary

JARVIS is a **local-first terminal agent** with:
- 10 modular skills (4 builtin + 6 external wrappers)
- 46 total LLM-callable commands
- 5 bundled MCP servers with console-script entry points
- Offline voice (STT/TTS/wake word)
- ChromaDB long-term memory with graceful degradation when embedding model is unavailable
- One-command installer

**Current verified status**:
- Circular import fixed; `python -m jarvis.main` launches without import errors
- TUI app constructs and initializes successfully with 46 commands registered
- All 10 tests in `tests/test_skills.py` pass
- Existing `tests/test_settings.py` passes
- Skill toggle changes persist to disk via `save_settings()`
- Skill command schemas are generated from handler signatures via `inspect.signature`

**Remaining gaps**:
- AgentLoop + LLM tool-call streaming integration lacks dedicated tests
- Full interactive TUI session not yet verified end-to-end
- Heavy import time (~20-30s) on first load due to `sentence_transformers` + `chromadb`
- MCP servers use outdated decorator API (`@server.list_tools()`) incompatible with installed `mcp` 2.1.1; requires migration to `on_list_tools`/`on_call_tool` constructor args
- Missing UI handlers: Add Memory, Install Skill, `/model`, token count updates

**Fixed in latest pass**:
- Subprocess cleanup in `JarvisApp.on_unmount()` for barehands/backtalk/visualizer
- Web search MCP server implemented (`jarvis/mcp/servers/web_search.py`)
- Filesystem MCP root changed from `~` to `project_root / "jarvis-fs"`
- Brittle `parents[4]` path resolution replaced with settings-based resolution in all 5 external skills
- Retry/backoff added to `LLMClient.chat()` with exponential backoff for transient failures
- MCP tool result parsing hardened in `jarvis/mcp/client.py`
- ToolsScreen now accepts optional `mcp_client` to share `AgentLoop.mcp` instance
- 9 new tests added (22 total pass); coverage for path resolution, retry logic, MCP parsing, cleanup, and web search server

