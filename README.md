# OpenJarvis

JARVIS - Just A Rather Very Intelligent System

A terminal-based AI assistant inspired by Iron Man's JARVIS from the Marvel Cinematic Universe. Built with Python, Textual, and local AI models.

## Features

- **Local AI First**: Runs entirely offline with Ollama (Llama 3.1, Qwen, etc.) or llama-cpp-python (direct GGUF inference). Also supports LM Studio, LocalAI, OpenAI, and Anthropic
- **Auto-Detection**: Probes all available providers on startup — Ollama → LM Studio → LocalAI → llama-cpp-python → OpenAI → Anthropic
- **Terminal UI**: Beautiful TUI built with Textual framework
- **Voice Support**: Offline STT (Vosk with auto-download / Whisper.cpp) + TTS (Piper with auto-download) + Sarvam AI cloud TTS/STT with language auto-detection
- **Wake Word**: Fully offline open-source wake word detection (openWakeWord — no API key needed) or Porcupine (auto-downloads .ppn)
- **MCP Tools**: 7 auto-discovered MCP servers (filesystem, terminal, git, memory, web_search, browser, desktop)
- **Skills System**: 10 modular skills (4 builtin + 6 external) with 47 total commands
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

> **First time?** Run `jarvis --install` after installing to auto-detect AI providers and download all voice models.
>
> **Friends having trouble?** See `scripts/setup_friend.sh` for a guided step-by-step setup that handles pipx installation, PATH configuration, and initial setup automatically.

The installer auto-detects available AI providers (Ollama, LM Studio, LocalAI, llama-cpp-python) and
downloads all voice models (Piper TTS, Vosk/Whisper STT, openWakeWord wake word) on first run.

## Current Capabilities — What JARVIS Can Do

### ✅ Fully Working

| Area | Status | Details |
|------|--------|---------|
| **TUI Interface** | ✅ Functional | Textual-based terminal with chat, skills, tools, memory, settings, voice screens |
| **Skills System** | ✅ 47 commands | 4 builtin (system_monitor, code_assistant, memory, voice_control) + 6 external |
| **LLM: Ollama** | ✅ Streaming | Local models with tool-call support & exponential backoff retry |
| **LLM: Llama-cpp-python** | ✅ Streaming | Load `llama-cpp-python` GGUF models directly (no Ollama). Hermes 2 Pro, DeepSeek Coder supported |
| **LLM: LM Studio** | ✅ Auto-detected | Probes port 1234, auto-selects models via OpenAI-compatible API |
| **LLM: LocalAI** | ✅ Auto-detected | Probes port 8080/41523, OpenAI-compatible API |
| **MCP Client** | ✅ Auto-connect | Connects to all configured + auto-discovered servers; tools shared with AgentLoop |
| **MCP Servers** | ✅ 7 built-in | filesystem, terminal, git, memory, web_search, browser (Playwright), desktop (pyautogui) — auto-started as stdio subprocesses |
| **External Skills** | ✅ 10 skills | marketing, visualizer, memory_vault, barehands, backtalk, fullstack_agent — all with HTTP client integration |
| **Long-term Memory** | ✅ ChromaDB | Vector store with cosine similarity; embeddings lazy-loaded |
| **Voice: Wake Word** | ✅ Offline | openWakeWord (no API key!) or Porcupine with auto-download of `.ppn` |
| **Voice: TTS** | ✅ Auto-download | piper-tts Python package with HuggingFace voice auto-download; Sarvam cloud fallback |
| **Voice: STT** | ✅ Auto-download | Vosk (auto-downloads model) or Whisper.cpp (`pywhispercpp`, auto-downloads model) |
| **Builtin: System Monitor** | ✅ 6 commands | CPU, memory, disk, GPU, network, processes |
| **Builtin: Code Assistant** | ✅ 3 commands | AST analysis: read functions, find TODOs, file structure |
| **Builtin: Memory** | ✅ 3 commands | remember/recall/forget via ChromaDB |
|| **Builtin: Voice Control** | ✅ 4 commands | Voice on/off, test, language setting (`/language hi-IN`) |
|| **Builtin: Browser** | ✅ 9 commands | Navigate, click, type, screenshot, scroll, wait via Playwright |
|| **Builtin: Desktop** | ✅ 7 commands | Mouse/keyboard control, screenshots via pyautogui |
|| **MCP: Browser** | ✅ 10 tools | Playwright browser automation (navigate, click, type, screenshot) |
|| **MCP: Desktop** | ✅ 7 tools | pyautogui desktop control (mouse, keyboard, hotkey, screenshot) |
|| **Voice: Wake Word** | ✅ Offline | openWakeWord (no API key!) or Porcupine with auto-download of `.ppn` |

### 🚧 Future Roadmap

| Priority | Area | Plan |
|----------|------|------|
| **High** | OpenAI/Anthropic cloud APIs | Full SDK integration with streaming — already supported, just install `openai`/`anthropic` + set `JARVIS_LLM_API_KEY` (LM Studio/LocalAI remain the free local alternatives) |
| **High** | Voice hardware testing | Testing with real microphone + speakers (wake word detection, STT capture, TTS playback) |
| **Medium** | Sarvam AI rate-limit handling | Add retry middleware with exponential backoff for cloud API calls |
| **Medium** | Real-time audio streaming | Low-latency chunked STT streaming |
| **Medium** | Voice Activity Detection (VAD) | Silence detection for smarter voice activation |
| **Low** | Multi-modal input | Image input support for vision-capable LLMs |

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

All models auto-download on first run:
- **Piper voices**: Downloaded to `~/.jarvis/voice/` via HuggingFace
- **Vosk STT models**: Downloaded to `~/.jarvis/voice/`
- **Whisper models**: Downloaded to `~/.local/share/pywhispercpp/`
- **openWakeWord models**: Downloaded on first import
- **Porcupine .ppn**: Downloaded from HuggingFace (access key still required)

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
| **MCP** | 5 built-in servers | ✅ Auto-connect | mcp package |

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
```bash
jarvis-mcp-filesystem --root /path/to/project
jarvis-mcp-terminal --allow ls,cat,git
jarvis-mcp-git --repo /path/to/repo
jarvis-mcp-memory --path ~/.jarvis/memory
jarvis-mcp-browser --headless  # or --headed for visible browser
jarvis-mcp-desktop             # no flags needed
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