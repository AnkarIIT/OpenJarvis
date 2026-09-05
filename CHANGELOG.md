# Changelog

All notable changes to the OpenJarvis project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — Multi-Provider LLM & Internet Download Stack
- **LLM auto-detection** — `provider="auto"` probes Ollama → LM Studio → LocalAI → llama-cpp-python → OpenAI → Anthropic in priority order
- **LM Studio support** — `_chat_openai_compatible()` OpenAI-compatible API client probing port 1234
- **LocalAI support** — probes ports 8080/41523, OpenAI-compatible API
- **OpenAI/Anthropic support** — full streaming chat via `httpx` (OpenAI) and `anthropic` package (Claude)
- **GGUF direct download** — installer downloads GGUF models from HuggingFace (Hermes 2 Pro, DeepSeek Coder, Qwen, Llama 3.1)
- **Agentic AI models** — Hermes 2 Pro Llama 3 8B, DeepSeek Coder 6.7B support via GGUF
- **HTTP client for backtalk** — `_set_state()` and `_set_mood()` now POST to `http://127.0.0.1:{port}` (HTTP first, file-based fallback)
- **HTTP client for backtalk status** — `_status()` now GETs `http://127.0.0.1:{port}/state` (HTTP first, file-based fallback)
- **Auto-download openWakeWord models** — on first import
- **Auto-download Porcupine .ppn** — from HuggingFace if not present
- **Web search MCP server** — added to installer auto-config (was missing from `_setup_mcp_servers`)
- **Async file download** — `_download_file()` with rich progress bars in installer
- **Zip extraction** — `_extract_zip()` for Vosk model downloads

### Changed — Multi-Provider LLM
- **`provider` default** changed from `"ollama"` to `"auto"` — auto-detects best available provider
- **Settings** — added `auto_detect: bool` and `"auto"` to provider Literal type
- **`detect_provider()`** — new function for one-off provider detection
- **`_probe_provider()`** — new function to probe each provider's availability
- **`provider_name` property** — LLMClient exposes resolved provider name
- **`list_models()`** — now supports all 6 providers (Ollama, LM Studio, LocalAI, llama_cpp, Anthropic)
- **`pull_model()`** — supports GGUF download (llama_cpp), Ollama pull, and informational messages for external providers
- **`chat()`** — routes to correct handler based on resolved provider with fallback to `_chat_fallback()`

### Changed — External Skills HTTP Clients
- **backtalk `_set_state()`** — HTTP POST to `/state` with file-based fallback
- **backtalk `_set_mood()`** — HTTP POST to `/mood` with file-based fallback
- **backtalk `_status()`** — HTTP GET to `/state` with file-based fallback
- **backtalk `_start()`** — no longer conflicts with barehands port (port 8795)

### Changed — Installer Auto-Download
- **`VOICE_MODELS`** — expanded to include openWakeWord, Whisper, and Porcupine models
- **`_recommend_and_install()`** — handles `llama_cpp` (GGUF download), `lm_studio`, `localai` providers
- **`_download_gguf_model()`** — new method for direct GGUF download with progress bar
- **`_download_voice_models()`** — rewritten with async download, progress bars, zip extraction
- **`_setup_mcp_servers()`** — now includes all 5 servers (added web_search)
- **Detection table** — shows running status and API URL for LM Studio/LocalAI

### Changed — Detectors
- **`check_lm_studio()`** — now probes HTTP API at port 1234 for running models + cached .gguf files
- **`check_localai()`** — new function, probes ports 8080/41523
- **`detect_all_local_ai()`** — added `localai` to detection results
- **`get_available_models()`** — added 5 GGUF download options (Llama 3.1, Qwen 2.5, Phi-3, Hermes 2 Pro, DeepSeek Coder)

### Changed — Settings
- **`LLMSettings.provider`** — default `"ollama"` → `"auto"`, added `"lm_studio"`, `"localai"` options
- **`LLMSettings`** — added `auto_detect` field
- **`VoiceSettings.wake_word_engine`** — already had `"auto"` option

### Changed — README
- Added LM Studio, LocalAI, OpenAI/Anthropic to Features
- Added auto-detection priority chain
- Added Environment Variables reference table (8 vars)
- Added Model Management section (`--models`, `--pull`)
- Added Supported Agentic AI Models table (Hermes 2 Pro, DeepSeek Coder, Qwen, Llama 3.1)
- Updated Capabilities table (LM Studio, LocalAI, External Skills HTTP)
- Updated Cloud Features section (OpenAI/Anthropic now supported)
- Updated Acknowledgments with new project links
- Updated offline stack summary table
- Fixed `--no-ollama` → `llama_cpp` provider mode reference

### Changed — CLI
- `main.py`: added `--models`/`-m` to list all detected providers + installable models
- `main.py`: added `--pull <model>`/`-p` to download a specific model via LLMClient

### Changed — Tests
- `test_settings_defaults` — updated for `provider="auto"` default
- `test_settings_serialization` — updated for `"auto"` default
- `test_llm_client_retryable_error_is_retried` — explicit `provider="ollama"` to bypass auto-detection
- `test_llm_client_non_retryable_error_raises` — explicit `provider="ollama"` to bypass auto-detection

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
