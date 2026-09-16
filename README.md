# OpenJarvis

JARVIS - Just A Rather Very Intelligent System

A terminal-based AI assistant inspired by Iron Man's JARVIS from the Marvel Cinematic Universe. Built with Python, Textual, and local AI models.

## Features

- **Local AI First**: Runs entirely offline with Ollama (Llama 3.1, Qwen, etc.) or llama-cpp-python (direct GGUF inference). Also supports LM Studio, LocalAI, OpenAI, and Anthropic
- **Auto-Detection**: Probes all available providers on startup — Ollama → LM Studio → LocalAI → llama-cpp-python → OpenAI → Anthropic
- **Terminal UI**: Beautiful TUI built with Textual framework
- **Voice Support**: Offline STT (Vosk with auto-download / Whisper.cpp) + TTS (Piper with auto-download) + Sarvam AI cloud TTS/STT with language auto-detection
- **Wake Word**: Fully offline open-source wake word detection (openWakeWord — no API key needed) or Porcupine (auto-downloads .ppn)
- **MCP Tools**: 7 built-in servers with safe-by-default filtering
- **Skills System**: Built-in and user-installed skills with manifest validation
- **Long-term Memory**: Vector-based memory with ChromaDB + sentence-transformers
- **External Integration**: Wraps 6 external AI projects as native JARVIS skills with HTTP client communication
- **Automated Setup**: One-command installation with auto-detection + auto-download of all models

## Quick Start

### Option 1: pipx (Recommended)

```powershell
# Windows (PowerShell):
python -m pip install pipx
pipx install git+https://github.com/AnkarIIT/OpenJarvis.git

# Linux/Mac:
python3 -m pip install --user pipx
pipx install git+https://github.com/AnkarIIT/OpenJarvis.git
```

### Option 1A: One-line Windows PowerShell bootstrap

For a fresh Windows machine, open **PowerShell as Administrator** and run:

```powershell
irm https://raw.githubusercontent.com/AnkarIIT/OpenJarvis/main/scripts/install_windows.ps1 | iex
```

The bootstrapper finds or installs Python 3.10+, upgrades pip, installs OpenJarvis with its
supported optional components, installs the Playwright Chromium runtime, and runs
`jarvis doctor --json`. It does not silently install Ollama models, grant dangerous MCP
permissions, or enable cloud services; those actions require an explicit choice and provider
configuration.

### Option 2: From source with setup script

```powershell
# Clone the repo
git clone https://github.com/AnkarIIT/OpenJarvis.git
cd OpenJarvis

# Run the setup script (use PowerShell on Windows, bash on Linux/Mac):
# Windows PowerShell:
.\scripts\setup_friend.ps1
# Git Bash / MSYS on Windows:
bash scripts/setup_friend.sh
# Linux/Mac:
bash scripts/setup_friend.sh
```

### Option 3: Direct pip install

```powershell
# Clone, then install:
git clone https://github.com/AnkarIIT/OpenJarvis.git
cd OpenJarvis
pip install -e .
# If jarvis command is not found, add Python Scripts to PATH:
# Windows PowerShell: [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';C:\Users\<you>\AppData\Roaming\Python\Python314\Scripts', 'User')
# Then restart your terminal.
```

### Start JARVIS

```powershell
jarvis
# First time? Run: jarvis --install  (auto-detects AI providers + downloads voice models)
```

> **First time?** Run `jarvis --install` after installing to detect providers and configure optional components.
>
> **Friends having trouble?** See `scripts/setup_friend.sh` for a guided step-by-step setup that handles pipx installation, PATH configuration, and initial setup automatically.

The installer detects available AI providers and installs selected optional dependencies. Voice models
and native audio backends are optional and may require additional downloads and hardware.

## Where JARVIS Stands

JARVIS is a working local-assistant platform, not a fully autonomous always-on agent. Installation,
CLI/TUI startup, configuration, memory, skills, MCP discovery, safety defaults, provider detection,
and diagnostics are implemented and covered by automated tests. The latest local validation passed
**31 tests**; CI targets Python 3.10–3.13.

| Area | Current status |
|------|---------------|
| Installation and editable install | Working on supported Python versions |
| CLI, TUI, and configuration persistence | Working |
| Provider detection and chat | Working when a provider/model is available |
| Ollama and OpenAI-compatible providers | Streaming and tool-call paths implemented |
| llama.cpp/GGUF provider | Implemented; requires a local GGUF model and optional dependency |
| Anthropic provider | Implemented, but less exercised than local providers |
| Provider diagnostics | `jarvis doctor --json` reports provider/model, attempts, retries, fallbacks, latency, and errors |
| Skills | Built-in and external skills load with optional-dependency isolation |
| User extensions | Add/remove/enable/disable skills and configure MCP servers |
| Skill manifests | Validates names, permissions, dependencies, and supported platforms |
| Memory | ChromaDB semantic memory with retention and secret filtering |
| MCP discovery | Implemented with persistent sessions and compatibility serialization |
| MCP recovery | One bounded reconnect attempt after a failed tool call; full supervision remains future work |
| Agent task state | Each run has an ID and reports running, completed, failed, or cancelled state |
| Action audit log | Enabled by default at `~/.jarvis/audit.jsonl`; sensitive argument keys are redacted |
| MCP safety defaults | Memory and web search allowed by default; dangerous servers require explicit opt-in |
| Voice imports | CI/headless-safe |
| Real voice operation | Requires optional packages, native audio, models, and hardware testing |
| Automated tests | 31 local tests passing; CI matrix covers Python 3.10–3.13 |

## What JARVIS Can Do

- Chat and stream responses through Ollama, llama.cpp/GGUF, LM Studio, LocalAI, OpenAI-compatible
  APIs, and Anthropic when configured.
- Reply in the language used by the user when language auto-detection is enabled. A fixed response
  language can also be configured with `voice.language` or the `language` skill command. Voice
  recognition quality still depends on the selected STT engine and its installed language model.
- Detect providers, retry some transient failures, and expose provider diagnostics.
- Execute structured LLM tool calls through the agent loop.
- Provide a Textual terminal interface and CLI commands for setup, diagnostics, permissions, models,
  skills, MCP servers, and tools.
- Monitor CPU, memory, disk, GPU, network, and processes.
- Inspect source-code structure, functions, and TODOs.
- Store, search, expire, and forget semantic memories while rejecting obvious secrets by default.
- Install local/Git skills, enable or disable skills, and validate skill manifests.
- Connect to filesystem, terminal, Git, memory, web-search, browser, and desktop MCP servers when
  permitted by configuration.
- Use Playwright browser automation and PyAutoGUI desktop automation when optional dependencies and
  a suitable local environment are available.
- Use Vosk/Whisper speech-to-text, Piper/Sarvam text-to-speech, and wake-word integrations when
  required packages, models, native audio, and hardware are present.
- When a supported wake-word engine detects the configured wake word, JARVIS stops wake-word
  capture briefly, speaks **“Hello Master”**, listens for the next command, and then rearms the
  wake-word listener. The greeting can be changed with `voice.wake_word_greeting`.

## What JARVIS Cannot Reliably Do Yet

- It cannot produce answers without an active compatible LLM provider and model.
- It is not a production-grade autonomous supervisor: durable background tasks, approvals, rollback,
  crash recovery, resource limits, and runaway-action prevention are incomplete.
- MCP lifecycle supervision is incomplete. The client now records basic server health and attempts
  one bounded reconnect after a failed tool call, but restart limits, backoff, timeouts, and durable
  per-server metrics are not yet production-ready.
- Permissions are primarily server-level. Complete per-tool approval is not implemented; for example,
  Git status cannot yet be independently allowed while commits require confirmation.
- Voice is not fully validated on real hardware. Microphone capture, speaker output, wake-word
  reliability, noise handling, VAD, barge-in, and long-running sessions still need testing.
- Vision and multimodal understanding are limited; screenshots, camera frames, documents, and video
  are not yet a mature general-purpose input pipeline.
- External skills are not all self-contained. Some require separate projects, services, playbooks, or
  dependencies that are not bundled with this repository.
- Cloud-provider behavior is not completely uniform. Anthropic streaming/tool-call behavior and
  provider-specific error handling need broader end-to-end coverage.
- There is no mature multi-user profile, private/shared memory separation, or timezone-aware
  personal-preference system.

## Recommended Next Milestones

1. Add per-tool permissions, confirmation prompts, and audit logs.
2. Add MCP health checks, timeouts, bounded restart/backoff, and server metrics.
3. Build a fake-provider/fake-MCP end-to-end harness for fallback, denial, timeout, and crash cases.
4. Complete real Windows voice hardware validation.
5. Expand provider, extension, and multimodal integration tests.

## Requirements

- Python 3.10+
- 8GB+ RAM (for Llama 3.1 8B) or GPU (for faster inference)
- Ollama (for LLM) — auto-installed by `jarvis --install`
- Optional: Local LLM model (GGUF for `llama_cpp` provider mode)

### Full Offline Mode

For completely offline voice + LLM:
```bash
pip install -e ".[offline]"
# Downloads:
# - llama-cpp-python (GGUF model support)
# - openwakeword (no API key needed!)
# - piper-tts (Python package, no CLI binary)
# - pywhispercpp (whisper.cpp Python bindings)
# - vosk (offline STT)
# - pvporcupine (optional, needs access key)
```

Then set `llama.cpp` as LLM provider:
```bash
export JARVIS_LLM_PROVIDER=llama_cpp
export JARVIS_LLM_MODEL_PATH=./models/llama-3.1-8b-instruct.Q4_K_M.gguf
export JARVIS_VOICE_STT_ENGINE=whisper  # or keep 'vosk'
```

Some optional models can download on first use:
- **Piper voices**: Downloaded to `~/.jarvis/voice/` when the Piper backend is selected
- **Vosk STT models**: Downloaded to `~/.jarvis/voice/` when Vosk is selected
- **Whisper models**: Downloaded by the selected Whisper backend
- **Wake-word models**: Downloaded by the selected wake-word backend

Downloads require network access and storage. Voice still requires a working native audio backend
and microphone/speaker hardware.

### Cloud Features (Optional)

- Sarvam AI API key (for Hindi/Indian language cloud TTS/STT)
- Picoville access key (for Porcupine wake word — or use openWakeWord instead)
- OpenAI API key (`JARVIS_LLM_API_KEY` with `provider=openai`) — for GPT-4o, o1, etc.
- Anthropic API key (`JARVIS_LLM_API_KEY` with `provider=anthropic`) — for Claude 3.5 Sonnet

### Offline Stack Summary

| Component | Offline Tech | Auto-Download | External Dep |
|-----------|-------------|---------------|--------------|
| **LLM** | Ollama / llama-cpp-python / LM Studio / LocalAI | Ollama: yes / GGUF: yes (auto-download from HF) / LM Studio,LocalAI: external GUI | llama-cpp-python pip package |
| **TTS** | piper-tts Python package | ✅ Yes (HuggingFace) | piper-tts pip package |
| **STT** | Vosk or Whisper.cpp | ✅ Yes | vosk or pywhispercpp |
| **Wake Word** | openWakeWord | ✅ Yes | openwakeword pip package |
| **Memory** | ChromaDB | ✅ Lazy load | sentence-transformers |
| **MCP** | 7 built-in servers | Filtered by safety policy | mcp package |

## Architecture

```
jarvis/
├── config/          # Settings & automated installer
├── tui/             # Textual-based terminal UI
├── agent/           # Agent loop & LLM client
├── voice/           # TTS (Piper), STT (Vosk), wake word
├── mcp/             # Model Context Protocol client & servers
├── skills/          # Skill system (builtin + user)
├── memory/          # Vector memory (ChromaDB)
└── utils/           # System detection, logging
```

## Built-in Skills

| Skill | Commands | Description |
|-------|----------|-------------|
| `system_monitor` | 6 | CPU, memory, disk, GPU, processes, network |
| `code_assistant` | 3 | Analyze code, list functions, find TODOs |
| `memory` | 3 | Remember, recall, forget memories |
| `voice_control` | 4 | Voice on/off, test, language setting |
| `browser` | 9 | Navigate, click, type, screenshot, scroll, wait |
| `autonomous` | Optional | Automation-related commands; not a production autonomous supervisor |
| `emotional` | Optional | Text/emotional analysis |
| `instant_learning` | Optional | Learning utilities |
| `multisensory` | Optional | Multisensory utilities |
| `predictive` | Optional | Prediction utilities |
| `traffic_camera` | Optional | Traffic-camera integration when dependencies are available |

## External Skills

| Skill | Commands | Wrapped Project | Mode |
|-------|----------|----------------|------|
| `marketing` | 3 | ai-marketing-skills | File I/O |
| `visualizer` | 6 | ai-visualizer | Subprocess + HTTP |
| `memory_vault` | 6 | ai-memory-vault | File I/O |
| `barehands` | 6 | barehands | Subprocess + HTTP |
| `backtalk` | 6 | backtalk | Subprocess + HTTP |
| `fullstack_agent` | 4 | fullstack-agent | File I/O + subprocess |

## MCP Servers

- **filesystem** (`jarvis-mcp-filesystem`) - File operations (sandboxed to project root)
- **terminal** (`jarvis-mcp-terminal`) - Safe command execution (whitelisted)
- **git** (`jarvis-mcp-git`) - Git operations (repo-aware)
- **memory** (`jarvis-mcp-memory`) - Persistent key-value storage
- **web_search** (`jarvis-mcp-web-search`) - Web search via DuckDuckGo
- **browser** (`jarvis-mcp-browser`) - Browser automation via Playwright (navigate, click, type, screenshot, scroll)
- **desktop** (`jarvis-mcp-desktop`) - Desktop control via pyautogui (mouse, keyboard, hotkey, screenshot)

### MCP Server CLI

All MCP servers accept flags via argparse:
```powershell
jarvis-mcp-filesystem --root /path/to/project
jarvis-mcp-terminal --allow ls,cat,git
jarvis-mcp-git --repo /path/to/repo
jarvis-mcp-memory --path ~/.jarvis/memory
jarvis-mcp-browser --headless
jarvis-mcp-desktop
```

### Extensions

JARVIS supports user-installed skills and configured MCP servers:

```powershell
jarvis list-skills
jarvis search-skills browser
jarvis add-skill .\my-skill
jarvis add-skill https://github.com/example/jarvis-skill.git
jarvis enable-skill my-skill
jarvis disable-skill my-skill
jarvis remove-skill my-skill

jarvis add-mcp my-server python --arg -m --arg my_mcp_server
jarvis list-mcp
jarvis remove-mcp my-server
jarvis list-tools
jarvis permissions
jarvis doctor --json
```

Memory is privacy-aware by default: entries that look like API keys, bearer
tokens, passwords, or private keys are rejected. Configure
`memory.retention_days` to automatically expire entries, or set
`memory.allow_sensitive` only when you explicitly need to store sensitive data.

MCP safety is server-level today. `memory` and `web_search` are allowed by default. `filesystem`,
`terminal`, `git`, `browser`, and `desktop` are disabled unless explicitly enabled with
`mcp.allow_dangerous` and, optionally, `mcp.enabled_servers`. There is not yet a confirmation
prompt for every individual write, delete, commit, or desktop action.

When dangerous MCP servers are enabled, `mcp.require_confirmation` defaults to `true` and the
agent blocks those actions unless an explicit confirmation interface approves them. This prevents
an LLM from silently writing files, executing commands, committing changes, navigating a browser,
or controlling the desktop.

Tool attempts are recorded in an append-only JSONL audit log by default. Set
`mcp.audit_enabled` to `false` to disable it or change `mcp.audit_path` to relocate it. Known
secret-like argument keys are redacted before being written.

Skills must contain `SKILL.md` or `skill.yaml`. User skills are installed under
`~/.jarvis/skills/` and can declare commands through a Python `skill.py` module.
MCP servers are stored in `~/.jarvis/config.json`; dangerous servers should be
added explicitly rather than enabled through automatic discovery. Enable dangerous servers only
on a trusted machine:

```json
{
  "mcp": {
    "allow_dangerous": true,
    "enabled_servers": ["memory", "web_search", "filesystem"]
  }
}
```

## Configuration

Config stored at `~/.jarvis/config.json`:

```json
{
  "llm": {"provider": "auto", "model": "llama3.1:8b"},
  "voice": {"enabled": true, "wake_word_enabled": true},
  "memory": {"enabled": true},
  "ui": {"theme": "jarvis"}
}
```

### Environment Variables

All settings can be configured via environment variables (prefix `JARVIS_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_LLM_PROVIDER` | `auto` | `auto`, `ollama`, `llama_cpp`, `lm_studio`, `localai`, `openai`, `anthropic` |
| `JARVIS_LLM_MODEL` | `llama3.1:8b` | Model name or HF repo ID |
| `JARVIS_LLM_MODEL_PATH` | — | Path to `.gguf` file (for `llama_cpp` provider) |
| `JARVIS_LLM_BASE_URL` | `http://localhost:11434` | API base URL for Ollama/LM Studio/LocalAI/OpenAI |
| `JARVIS_LLM_API_KEY` | — | API key for OpenAI/Anthropic (or leave blank for local) |
| `JARVIS_VOICE_STT_ENGINE` | `vosk` | `vosk`, `whisper`, or `sarvam` |
| `JARVIS_VOICE_TTS_ENGINE` | `piper` | `piper` or `sarvam` |
| `JARVIS_VOICE_WAKE_WORD_ENGINE` | `auto` | `auto`, `openwakeword`, or `porcupine` |

### Model Management

```bash
jarvis --install          # Auto-detect providers + download all models
jarvis --models           # List available models from all providers
jarvis --pull MODEL       # Download a specific model
```

### Auto-Detection Priority

When `provider="auto"`, JARVIS probes providers in this order:
1. **Ollama** (localhost:11434) — preferred for chat + tool use
2. **LM Studio** (localhost:1234) — OpenAI-compatible desktop app
3. **LocalAI** (localhost:8080/41523) — self-hosted OpenAI replacement
4. **llama-cpp-python** (local .gguf files) — no server needed
5. **OpenAI API** (requires API key)
6. **Anthropic API** (requires API key)

### Supported Agentic AI Models

JARVIS supports agentic AI models via direct GGUF download or Ollama:

| Model | Provider | Use Case |
|-------|----------|----------|
| Hermes 2 Pro Llama 3 8B | GGUF download | Agentic reasoning, tool use |
| DeepSeek Coder 6.7B | GGUF / Ollama | Code analysis, programming |
| Llama 3.1 8B Instruct | Ollama / GGUF | General chat, Q&A |
| Qwen 2.5 7B Instruct | Ollama / GGUF | Multilingual, coding |
| Phi-3 Mini | Ollama / GGUF | Low-RAM setups (2.3GB) |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+Q` | Quit |
| `Ctrl+C` | Clear chat |
| `Ctrl+K` | Command palette |
| `Ctrl+V` | Toggle voice |
| `Ctrl+1-7` | Switch tabs (Chat, Skills, Memory, Tools, Voice, Settings, Dashboard) |
| `F1` | Help |

### Dashboard Tab Shortcuts

When in the Dashboard screen (default on startup):
- **Ctrl+1** — Chat tab
- **Ctrl+2** — Skills tab (builtin + external skills list)
- **Ctrl+3** — Memory tab (ChromaDB memory viewer)
- **Ctrl+4** — Tools tab (all MCP tools grouped by server)
- **Ctrl+5** — Voice tab (voice configuration status)
- **Ctrl+6** — Settings tab
- **Ctrl+7** — Dashboard tab (system status + AI provider detection)
- **Esc** — Back to chat

## Voice Commands

- "Hey JARVIS" - Wake word (openWakeWord, no API key!)
- `Space` - Toggle continuous listening mode (in Voice screen)
- `/voice on` - Enable voice listening (via command palette)
- `/voice off` - Disable voice listening
- `/voice test` - Test TTS with custom message

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .

# Type check
mypy jarvis
```

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- Inspired by JARVIS from Marvel Cinematic Universe
- Built with [Textual](https://textual.textualize.io/)
- Local AI via [Ollama](https://ollama.com/) / [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) / LM Studio / LocalAI
- Voice via [Piper](https://github.com/rhasspy/piper) & [Vosk](https://alphacephei.com/vosk/) & [openWakeWord](https://github.com/dscripka/openwakeword)
- Browser automation via [Playwright](https://playwright.dev/python/)
- Desktop automation via [pyautogui](https://github.com/asweigart/pyautogui)
- MCP via [Model Context Protocol](https://modelcontextprotocol.io/)