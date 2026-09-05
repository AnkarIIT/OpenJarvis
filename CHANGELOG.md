# Changelog

All notable changes to the OpenJarvis project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Complete offline-on-machine stack** — JARVIS can now run fully offline with zero external services:
  - **LLM: `llama-cpp-python`** provider for direct GGUF model inference (no Ollama needed)
    - New `_chat_llama_cpp()` async generator for streaming GGUF inference
    - Lazy model loading + caching via `settings.llm._llama_instance`
    - Set `JARVIS_LLM_PROVIDER=llama_cpp` and `JARVIS_LLM_MODEL_PATH=./model.gguf`
  - **TTS: `piper-tts` Python package** — rewritten `PiperTTS` class uses `PiperVoice` Python API directly (no CLI binary needed)
    - Auto-downloads voice models from HuggingFace on first run to `~/.jarvis/voice/`
    - Falls back to `PiperCLITTS` (legacy CLI binary) if Python package unavailable
    - Lazy voice loading in `speak()` via `_ensure_voice()`
  - **STT: `WhisperSTT`** using `pywhispercpp` (whisper.cpp Python bindings)
    - Fully offline, auto-downloads `base.en` whisper model on first use
    - Set `JARVIS_VOICE_STT_ENGINE=whisper`
  - **STT: Vosk auto-download** — `_ensure_vosk_model()` downloads model from alphacephei.com if not present
  - **Wake Word: `OpenWakeWordDetector`** — fully open-source, no Picoville access key needed
    - Uses `dscripka/openwakeword` with auto-downloaded models
    - Set `JARVIS_VOICE_WAKE_WORD_ENGINE=openwakeword`
    - `wake_word_engine: "auto"` tries openWakeWord first, then Porcupine, then Mock
  - **Porcupine auto-download** — `_ensure_porcupine_model()` downloads `.ppn` from HuggingFace
  - **MCP auto-discovery** — 5 built-in MCP servers auto-started as stdio subprocesses
    - `_BUILTIN_MCP_SERVERS` dict in `jarvis/mcp/client.py`
    - `mcp.auto_discover: True` setting auto-connects all built-in servers
- **`offline` optional dependency group** — `pip install -e ".[offline]"` installs all offline packages at once
  - llama-cpp-python, openwakeword, piper-tts, pywhispercpp, vosk, pvporcupine
- **Offline stack documentation** in README with requirements, auto-download locations, and install commands

### Added (existing)
- **Sarvam AI provider**: New TTS/STT provider using Sarvam AI REST APIs
  - `SarvamTTS` class with Bulbul v3/v2 voice models
  - `SarvamSTT` class with Saaras v3/v4 speech recognition
  - Configurable parameters: `sarvam_api_key`, `sarvam_tts_model`, `sarvam_stt_model`, `sarvam_tts_speaker`, `sarvam_tts_pace`, `sarvam_tts_temperature`
  - `'sarvam'` available as `tts_engine` and `stt_engine` option
  - Uses `aiohttp` for async HTTP requests
- **Language support**: BCP-47 language codes (e.g., `en-IN`, `hi-IN`)
  - `language` field in `VoiceSettings` (default: `en-IN`)
  - `lang` and `language_detection` fields in `SarvamSTT`
  - `VoicePipeline.set_language()` method
  - `/language` command in `VoiceControlSkill`
  - Language selector in `SettingsScreen`
- **External skill wrappers** (6 skills, 46+ commands):
  - `marketing` — wraps ai-marketing-skills (3 commands)
  - `visualizer` — wraps ai-visualizer (6 commands)
  - `memory_vault` — wraps ai-memory-vault (6 commands)
  - `barehands` — wraps barehands (6 commands)
  - `backtalk` — wraps backtalk (6 commands)
  - `fullstack_agent` — wraps fullstack-agent (4 commands)
- **MCP server: web_search** — DuckDuckGo-powered web search MCP server
- **MCP server console scripts** — 5 entry points: `jarvis-mcp-filesystem`, `jarvis-mcp-terminal`, `jarvis-mcp-git`, `jarvis-mcp-memory`, `jarvis-mcp-web-search`
- **LLM retry logic** — `_with_retry()` with exponential backoff in `LLMClient`
- **Shared MCPClient** — single client instance shared between AgentLoop and ToolsScreen
- **22 unit tests** in `tests/test_skills.py` and `tests/test_settings.py`

### Changed
- **MCP migration** — Migrated all 5 MCP servers (`filesystem.py`, `terminal.py`, `git.py`, `memory.py`, `web_search.py`) to `mcp` 2.1.1 callback API with `on_list_tools`/`on_call_tool` signatures
- **MCP server CLI** — All MCP servers now use `argparse` with `--root`/`--path`/`--allow` flags (backward compatible with positional args)
- **Skill registry** — `_load_external_skills()` auto-discovers and imports `skill.py` from `jarvis/skills/external/*/` directories
- **Path resolution** — External skills use `settings.project_root` instead of brittle `parents[4]`
- **Filesystem MCP root** — Changed default from `~` to `project_root / "jarvis-fs"`
- **`piper-tts`** moved to optional `voice` dependency group
- **`sentence-transformers`** added as core dependency (was missing)
- **`duckduckgo-search>=6.0`** added as dependency
- **`aiohttp>=3.9`** added as dependency
- **`backtalk_port`** default changed from `8794` to `8795` (avoid port conflict with `barehands_port`)
- **`.gitignore`** — Fixed `backtalk/` and `barehands/` patterns to use leading slashes (`/backtalk/`, `/barehands/`) to prevent matching nested directories

### Fixed
- `PROJECT_ROOT` undefined in `fullstack_agent/skill.py` — replaced with `_project_root` property that resolves via `settings.project_root` or `parents[4]` fallback
- `import asyncio` placement in `fullstack_agent/skill.py` — moved from bottom of file to top imports
- `SarvamTTS._play_wav` — fixed `wave.WaveReader` → `wave.open`, `read_frames()` → `readframes()`, `get_sample_width()` → `getsampwidth()`
- `SarvamTTS.__init__` — fixed `"sarvin_tts_temperature"` typo → `"sarvam_tts_temperature"`
- `barehands/skill.py` line 182 — added missing `f` prefix on f-string for port interpolation
- `JarvisApp.on_mount()` — now calls `agent_loop.initialize()` to connect MCP servers, initialize vector store, and load skills
- `JarvisApp.on_unmount()` — now calls `mcp.disconnect_all()` to clean up MCP sessions
- `CommandPalette.run_command()` — `/model` now switches to settings screen (was reopening palette); `/install` handler implemented
- `StatusBar` — added missing `ComposeResult` import from `textual.app`
- `command_palette.py` — moved `Horizontal` import to top-level (was at bottom of file)
- `AgentLoop._execute_tool` — checks tool name source (MCP vs skills) before calling, avoiding MCP timeout for local skill commands
- `AgentLoop._merge_tools` — `mcp_names` set now used for namespace collision detection
- `parse_nested` validator — added `"external"` field to validation
- `VoiceScreen` — TTS/STT engine labels now read from `settings.voice` instead of hardcoding "Piper"/"Vosk"
- `VoicePipeline` wiring — moved from `__init__` to `on_mount` (after `skill_registry.initialize()`)
- `switch_screen()` — guard against `None` voice screen when voice is disabled
- `_execute_tool` — replaced fragile `"error" not in mcp_result` check with explicit tool name resolution

## [Known Issues]

- **Sentence-transformers model**: `nomic-embed-text` requires internet access to download from HuggingFace on first run
- **Voice pipeline**: Requires hardware testing (wake word, STT, TTS) on real microphone/speakers
- **MCP servers**: Not yet tested as standalone stdio servers via console scripts
- **Security**: Terminal MCP server executes arbitrary shell commands (whitelisted by base command name only)
- **`asyncio_mode` warning**: `pyproject.toml` sets `asyncio_mode = "auto"` but `pytest-asyncio` may not be installed; tests use manual `asyncio.run()` wrappers
