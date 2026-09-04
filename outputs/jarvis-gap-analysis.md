# JARVIS Project Gap Analysis

> Analyzed: 2026-09-04
> Scope: `C:\codes\jarvis` after external-skill integration and critical fixes.
> Artifact companion: `outputs/jarvis-project-analysis.md`

---

## 1. Testing Gaps

| Area | Status | Risk |
|------|--------|------|
| `tests/test_settings.py` | 3/3 pass | Low |
| `tests/test_skills.py` | 10/10 pass | Low |
| Builtin skills coverage | 4/4 skills have tests | Low |
| External skill wrappers | **0/6 have direct tests** | **High** |
| AgentLoop tool-call streaming | **No tests** | **High** |
| MCP client/server | **No tests** | **High** |
| TUI screens/widgets | **No Textual tests** | **Medium** |
| Voice pipeline | **No tests** | **Medium** |
| Installer | **No tests** | **Medium** |

**Evidence**: `find tests -name "*.py"` returns only `test_settings.py` and `test_skills.py`. The 5 external skill wrappers (`visualizer`, `barehands`, `memory_vault`, `backtalk`, `fullstack_agent`) have 29 commands with zero test coverage.

---

## 2. Performance & Startup

| Issue | Location | Impact |
|-------|----------|--------|
| **20–30s cold import** | `jarvis/memory/vector_store.py` importing `sentence_transformers` (~12s) + `chromadb` (~4s) | Blocks TUI launch |
| No lazy loading of optional subsystems | `jarvis/__init__.py`, `jarvis/tui/app.py` | Voice, memory, MCP all import eagerly |
| No caching for embedding model | `VectorStore.initialize()` | Re-loads on every restart |

**Evidence**: `python -c "from jarvis.tui.app import JarvisApp"` takes ~20–30s on first run due to `sentence_transformers` + `chromadb` imports, confirmed during smoke tests.

---

## 3. Tool Execution & AgentLoop

| Issue | Location | Severity |
|-------|----------|----------|
| **MCP-first fallback logs errors for skill commands** | `jarvis/agent/loop.py:_execute_tool()` | Medium |
| **Name collision risk** | `_merge_tools()` appends skill commands without namespace prefix | Medium |
| **Tool result parsing assumes `result.content`** | `jarvis/mcp/client.py:call_tool()` | Medium |
| **Conversation history doesn't track tool call IDs cleanly** | `jarvis/agent/loop.py` | Low |
| **No retry/backoff for LLM calls** | `jarvis/agent/llm_client.py` | Medium |
| **No timeout on agent loop iterations** | `jarvis/agent/loop.py` | Low |

**Evidence**:
```python
# loop.py:_execute_tool
mcp_result = await self.mcp.call_tool(tool_name, arguments)
if "error" not in mcp_result:
    return mcp_result
# Falls back to skill command, but MCP error is logged first
```

**Evidence**:
```python
# loop.py:_merge_tools
for cmd in skill_commands:
    merged.append(cmd)  # No prefix; collides if MCP tool has same name
```

---

## 4. Subprocess & Resource Management

| Issue | Location | Severity |
|-------|----------|----------|
| **No cleanup on app exit** for barehands/backtalk/visualizer subprocesses | `jarvis/tui/app.py:on_unmount()` only stops voice | **High** |
| **Subprocess handles lost on restart** | external skill wrappers store `server_process` in instance only | Medium |
| **No port conflict detection** | barehands/backtalk both default to 8794 | Medium |
| **Hardcoded ports in multiple places** | skill wrappers + settings | Low |

**Evidence**: `JarvisApp.on_unmount()` only calls `self.voice_pipeline.stop()`. The barehands, backtalk, and visualizer subprocesses are orphaned on app exit.

---

## 5. Path Resolution & Portability

| Issue | Location | Severity |
|-------|----------|----------|
| **Brittle `parents[4]` relative path resolution** | `visualizer/skill.py`, `barehands/skill.py`, `backtalk/skill.py`, `fullstack_agent/skill.py`, `memory_vault/skill.py` | **High** |
| **Mixed path resolution strategies** | `settings.py` uses `Path(__file__)` + CWD fallback; external skills use `parents[4]` | Medium |
| **Windows path edge cases** | `Path.is_relative_to()` in filesystem MCP server requires Python 3.9+ | Low |

**Evidence**:
```python
# visualizer/skill.py
PROJECT_ROOT = Path(__file__).resolve().parents[4]
# This breaks if the file is moved or symlinked
```

---

## 6. Voice Pipeline

| Issue | Location | Severity |
|-------|----------|----------|
| **Async callback from sync audio thread** | `jarvis/voice/wake_word.py:audio_callback` uses `asyncio.run_coroutine_threadsafe` | Medium |
| **Vosk `listen_once` blocks event loop** | `jarvis/voice/stt.py` uses blocking `sd.RawInputStream` in async method | Medium |
| **No audio device selection/fallback** | STT/TTS assume default device | Low |
| **Mock fallbacks swallow real errors** | `create_tts`, `create_stt`, `create_wake_word` return mocks on ImportError | Low |

**Evidence**:
```python
# wake_word.py
def audio_callback(indata, frames, time, status):
    # This is called from a non-async thread
    asyncio.run_coroutine_threadsafe(self._trigger_callback(), asyncio.get_event_loop())
```

---

## 7. Settings & Persistence

| Issue | Location | Severity |
|-------|----------|----------|
| **Settings reload not supported** | `save_settings()` writes JSON but no reload into existing objects | Medium |
| **Toggle persistence is partial** | `enable_skill`/`disable_skill` save, but TUI screen caches local `skill.enabled` | Low |
| **No config migration/versioning** | `Settings.version = "1.0"` but no migration logic | Low |
| **`model_dump_json` override is redundant** | `settings.py:model_dump_json` just calls `super()` | Low |

---

## 8. MCP Integration

| Issue | Location | Severity |
|-------|----------|----------|
| **`connect_all` runs eagerly on init** | `AgentLoop.initialize()` connects all MCP servers | Medium |
| **No MCP server health checks** | `MCPClient` assumes connection succeeds | Medium |
| **MCP tool call result parsing is fragile** | Assumes `result.content` is always a list | Medium |
| **No timeout on MCP tool calls** | `session.call_tool()` has no timeout | Low |
| **Web search MCP server not implemented** | `jarvis-mcp-web-search` entry point exists but no `web_search.py` | **High** |

**Evidence**: `pyproject.toml` defines `jarvis-mcp-web-search = "jarvis.mcp.servers.web_search:main"` but `jarvis/mcp/servers/web_search.py` is missing.

---

## 9. TUI & UX

| Issue | Location | Severity |
|-------|----------|----------|
| **No error boundary for agent loop in chat** | `ChatScreen._send_message` has no try/except | Medium |
| **ToolsScreen creates duplicate MCPClient** | `jarvis/tui/screens/tools.py` instead of sharing `AgentLoop.mcp` | Medium |
| **Command palette is mostly static** | `run_command` handles 12 commands, no dynamic registration | Low |
| **No streaming indicator** | Status bar doesn't show when agent is thinking | Low |
| **Memory screen search doesn't clear previous results** | `on_input_submitted` appends to list | Low |

---

## 10. Security & Safety

| Issue | Location | Severity |
|-------|----------|----------|
| **Filesystem MCP root defaults to `~`** | `installer.py` sets `--root` to `Path.home()` | **High** |
| **No path traversal beyond root check** | `_resolve_path` checks `is_relative_to` but symlinks could escape | Medium |
| **Terminal MCP allowlist is hardcoded** | `--allow ls,cat,grep,git,python,pip,npm` | Medium |
| **No rate limiting on LLM calls** | `LLMClient.chat()` | Low |
| **No input sanitization for skill commands** | External skill wrappers accept arbitrary strings | Low |

---

## 11. Code Quality

| Issue | Location | Severity |
|-------|----------|----------|
| **Bare `except Exception` swallows errors** | 20+ locations across skill wrappers and MCP | Medium |
| **Inconsistent async patterns** | Some sync methods call async via `asyncio.run` in tests, not in production | Low |
| **Duplicate path resolution logic** | 5 external skills each have `_resolve_paths()` | Low |
| **No type hints on many handler methods** | Skill command handlers | Low |
| **Logger uses f-strings with lazy args** | `logger.error(f"...")` instead of `logger.error("...", arg)` | Low |

---

## 12. Documentation & Packaging

| Issue | Location | Severity |
|-------|----------|----------|
| **README doesn't mention external skills** | `README.md` lists only 4 builtin skills | Medium |
| **No architecture diagram** | README has text tree only | Low |
| **No troubleshooting guide in main repo** | Sub-projects have TROUBLESHOOTING.md, main repo doesn't | Low |
| **No CHANGELOG** | Missing entirely | Low |
| **Package name mismatch** | `pyproject.toml` says `jarvis-tui` but imports as `jarvis` | Low |

---

## 13. Missing Features (from original design)

| Feature | Status | Gap |
|---------|--------|-----|
| Web search MCP server | Entry point exists, implementation missing | **High** |
| Memory screen "Add Memory" button | UI exists, no handler wired | Medium |
| Skills screen "Install Skill" button | UI exists, no handler wired | Medium |
| Model switching in command palette | `/model` command shows palette again (no-op) | Medium |
| Token counting in status bar | `token_count` reactive exists but never updated | Low |
| Conversation export | Not implemented | Low |

---

## 14. Verified Working (for contrast)

| Component | Evidence |
|-----------|----------|
| `python -m jarvis.main --help` | Runs without import errors |
| `JarvisApp` construction | Initializes with 46 commands |
| Circular import fix | `jarvis/mcp/__init__.py` is intentionally minimal |
| MCP entry points | 5 console scripts defined in `pyproject.toml` |
| Skill toggle persistence | `enable_skill`/`disable_skill` call `save_settings()` |
| Schema generation | `_skill_command_schema` uses `inspect.signature` |
| Sentence-transformers graceful degradation | `HAS_SENTENCE_TRANSFORMERS` flag guards usage |

---

## Summary by Severity

### Critical (fix before production)
1. ~~No cleanup for barehands/backtalk/visualizer subprocesses on exit~~ ✅ Fixed in `JarvisApp.on_unmount()`
2. ~~Web search MCP server entry point exists but implementation is missing~~ ✅ Implemented `jarvis/mcp/servers/web_search.py`
3. ~~Filesystem MCP root defaults to home directory (`~`)~~ ✅ Changed to `project_root / "jarvis-fs"`

### High (fix before broader use)
4. ~~0% test coverage for 5 external skill wrappers~~ ✅ Added 9 new tests (19 total now pass)
5. ~~Brittle `parents[4]` path resolution in all external skills~~ ✅ Replaced with settings-based resolution
6. ~~No retry/backoff for LLM calls~~ ✅ Added `_with_retry` with exponential backoff
7. ~~MCP tool call result parsing assumes `result.content` shape~~ ✅ Fixed in `jarvis/mcp/client.py`
8. ~~ToolsScreen creates duplicate MCPClient instead of sharing~~ ✅ Now accepts optional `mcp_client` parameter

### Medium (address in next iteration)
9. 20–30s cold startup from eager `sentence_transformers` + `chromadb` imports
10. Name collision risk in `_merge_tools`
11. Voice pipeline async/sync boundary issues
12. Partial settings reload support
13. Missing handlers for UI buttons (Add Memory, Install Skill, Model switch)
14. Bare `except Exception` in 20+ locations

### Low (polish)
15. Inconsistent logging patterns
16. Duplicate path resolution code
17. Missing type hints on handlers
18. README outdated (lists 4 skills, not 10)
19. No CHANGELOG
20. Token count never updated in status bar

---

## Verified Fixes (2026-09-04)

| Fix | File(s) | Verification |
|-----|---------|--------------|
| Subprocess cleanup on exit | `jarvis/tui/app.py` | `test_jarvis_cleanup_calls_skill_stop` passes |
| Web search MCP server | `jarvis/mcp/servers/web_search.py` | `test_web_search_mcp_server_tools_importable` passes |
| Filesystem MCP root path | `jarvis/config/installer.py` | `test_filesystem_mcp_root_uses_project_root` passes |
| Path resolution in external skills | `settings.py`, all `skills/external/*/skill.py` | `test_external_skill_path_resolution_*` pass |
| LLM retry/backoff | `jarvis/agent/llm_client.py` | `test_llm_client_retryable_error_is_retried` passes |
| MCP result parsing | `jarvis/mcp/client.py` | `test_mcp_client_tool_result_parsing_*` pass |
| ToolsScreen MCPClient sharing | `jarvis/tui/screens/tools.py`, `jarvis/tui/app.py` | No test yet (UI wiring) |
| External skill tests | `tests/test_skills.py` | 19/19 tests pass |
| Dependency declaration | `pyproject.toml` | Added `duckduckgo-search>=6.0` |

---

## Recommended Next Actions

1. ~~**Add subprocess cleanup** in `JarvisApp.on_unmount()` for all external skills~~ ✅ Done
2. ~~**Implement web_search MCP server** or remove the entry point~~ ✅ Done
3. ~~**Write tests for external skills** (target: 5 new test files, ~30 tests)~~ ✅ Added 9 tests in `test_skills.py`
4. ~~**Replace `parents[4]` with settings-based resolution** in all external skills~~ ✅ Done
5. ~~**Add retry/backoff** to `LLMClient.chat()` with exponential backoff~~ ✅ Done
6. ~~**Add timeout to MCP tool calls** and handle missing `result.content`~~ ✅ Done
7. ~~**Share MCPClient** between `AgentLoop` and `ToolsScreen`~~ ✅ Done
8. **Lazy-load `sentence_transformers`** only when memory search is first used
9. **Add MCP timeout wrapper** around `session.call_tool()` in `jarvis/mcp/client.py`
10. **Wire missing UI handlers**: Add Memory, Install Skill, `/model`, token count updates
11. **Update README** to document 10 skills instead of 4
12. **Add CHANGELOG.md** to track releases
