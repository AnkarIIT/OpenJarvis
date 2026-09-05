# OpenJarvis

JARVIS - Just A Rather Very Intelligent System

A terminal-based AI assistant inspired by Iron Man's JARVIS from the Marvel Cinematic Universe. Built with Python, Textual, and local AI models.

## Features

- **Local AI First**: Runs entirely offline with Ollama (Llama 3.1, Qwen, etc.) or llama-cpp-python (direct GGUF inference). Also supports LM Studio, LocalAI, OpenAI, and Anthropic
- **Auto-Detection**: Probes all available providers on startup — Ollama → LM Studio → LocalAI → llama-cpp-python → OpenAI → Anthropic
- **Terminal UI**: Beautiful TUI built with Textual framework
- **Voice Support**: Offline STT (Vosk with auto-download / Whisper.cpp) + TTS (Piper with auto-download) + Sarvam AI cloud TTS/STT with language auto-detection
- **Wake Word**: Fully offline open-source wake word detection (openWakeWord — no API key needed) or Porcupine (auto-downloads .ppn)
- **MCP Tools**: 5 auto-discovered MCP servers (filesystem, terminal, git, memory, web_search)
- **Skills System**: 10 modular skills (4 builtin + 6 external) with 47 total commands
- **Long-term Memory**: Vector-based memory with ChromaDB + sentence-transformers
- **External Integration**: Wraps 6 external AI projects as native JARVIS skills with HTTP client communication
- **Automated Setup**: One-command installation with auto-detection + auto-download of all models

## Quick Start

```bash
# Install with pipx (recommended)
pipx install git+https://github.com/AnkarIIT/OpenJarvis.git

# Or install from source
git clone https://github.com/AnkarIIT/OpenJarvis.git
cd OpenJarvis
pip install -e .

# One-command setup — auto-detects AI providers + downloads all voice models
jarvis --install

# Start JARVIS
jarvis
```

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
| **MCP Servers** | ✅ 5 built-in | filesystem, terminal, git, memory, web_search — auto-started as stdio subprocesses |
| **External Skills** | ✅ 10 skills | marketing, visualizer, memory_vault, barehands, backtalk, fullstack_agent — all with HTTP client integration |
| **Long-term Memory** | ✅ ChromaDB | Vector store with cosine similarity; embeddings lazy-loaded |
| **Voice: Wake Word** | ✅ Offline | openWakeWord (no API key!) or Porcupine with auto-download of `.ppn` |
| **Voice: TTS** | ✅ Auto-download | piper-tts Python package with HuggingFace voice auto-download; Sarvam cloud fallback |
| **Voice: STT** | ✅ Auto-download | Vosk (auto-downloads model) or Whisper.cpp (`pywhispercpp`, auto-downloads model) |
| **Builtin: System Monitor** | ✅ 6 commands | CPU, memory, disk, GPU, network, processes |
| **Builtin: Code Assistant** | ✅ 3 commands | AST analysis: read functions, find TODOs, file structure |
| **Builtin: Memory** | ✅ 3 commands | remember/recall/forget via ChromaDB |
| **Builtin: Voice Control** | ✅ 4 commands | Toggle on/off, test, set language (`/language hi-IN`) |

### ❌ Cannot Do

| Area | Issue | Impact |
|------|-------|--------|
| **LLM: OpenAI/Anthropic** | Requires `openai`/`anthropic` pip packages + API key | Set `JARVIS_LLM_PROVIDER=openai` with `JARVIS_LLM_API_KEY`; LM Studio/LocalAI are better free options |
| **Voice: Hardware testing** | Requires real mic + speakers | Not tested with physical hardware |
| **Sarvam AI: Rate limits** | No rate-limit handling in API calls | May fail on burst usage |

### 🚧 In Development (Planned)

- Real-time audio streaming for STT
- Voice activity detection (VAD)
- Multi-modal capabilities (image input)
- Full OpenAI/Anthropic API integration (LM Studio/LocalAI are ready now)

## Requirements

- Python 3.10+
- 8GB+ RAM (for Llama 3.1 8B) or GPU (for faster inference)
- Ollama (for LLM) — auto-installed by `jarvis --install`
- Optional: Local LLM model (GGUF for `--no-ollama` mode)

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
- OpenAI/Anthropic API key (not yet implemented)

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

### MCP Server CLI

All MCP servers accept flags via argparse:
```bash
jarvis-mcp-filesystem --root /path/to/project
jarvis-mcp-terminal --allow ls,cat,git
jarvis-mcp-git --repo /path/to/repo
jarvis-mcp-memory --path ~/.jarvis/memory
```

## Configuration

Config stored at `~/.jarvis/config.json`:

```json
{
  "llm": {"provider": "ollama", "model": "llama3.1:8b"},
  "voice": {"enabled": true, "wake_word_enabled": true},
  "memory": {"enabled": true},
  "ui": {"theme": "jarvis"}
}
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+Q` | Quit |
| `Ctrl+C` | Clear chat |
| `Ctrl+K` | Command palette |
| `Ctrl+V` | Toggle voice |
| `Ctrl+T/G/M/O/Y/U` | Switch tabs |
| `F1` | Help |

## Voice Commands

- "Hey JARVIS" - Wake word
- `Ctrl+Space` - Push-to-talk
- Continuous listening mode available

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
- Local AI via [Ollama](https://ollama.com/)
- Voice via [Piper](https://github.com/rhasspy/piper) & [Vosk](https://alphacephei.com/vosk/)
- MCP via [Model Context Protocol](https://modelcontextprotocol.io/)