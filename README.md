# OpenJarvis

JARVIS - Just A Rather Very Intelligent System

A terminal-based AI assistant inspired by Iron Man's JARVIS from the Marvel Cinematic Universe. Built with Python, Textual, and local AI models.

## Features

- **Local AI First**: Runs entirely offline with Ollama (Llama 3.1, Qwen, etc.) or cloud providers (OpenAI, Anthropic)
- **Terminal UI**: Beautiful TUI built with Textual framework
- **Voice Support**: Offline STT (Vosk) + TTS (Piper), plus Sarvam AI cloud TTS/STT with language auto-detection
- **Wake Word**: "Hey JARVIS" activation (Porcupine)
- **MCP Tools**: 5 extensible tools via Model Context Protocol (filesystem, terminal, git, memory, web_search)
- **Skills System**: 10 modular skills (4 builtin + 6 external) with 47 total commands
- **Long-term Memory**: Vector-based memory with ChromaDB + sentence-transformers
- **External Integration**: Wraps 6 external AI projects as native JARVIS skills
- **Automated Setup**: One-command installation with auto-detection

## Quick Start

```bash
# Install with pipx (recommended)
pipx install git+https://github.com/AnkarIIT/OpenJarvis.git

# Or install from source
git clone https://github.com/AnkarIIT/OpenJarvis.git
cd OpenJarvis
pip install -e .

# Run installer (auto-detects and installs Ollama + models)
jarvis --install

# Start JARVIS
jarvis
```

## Current Capabilities — What JARVIS Can Do

### ✅ Working Now

| Area | Status | Details |
|------|--------|---------|
| **TUI Interface** | ✅ Fully functional | Textual-based terminal interface with chat, skills, tools, memory, settings, and voice screens |
| **Skills System** | ✅ 47 commands, 10 skills | 4 builtin (system_monitor, code_assistant, memory, voice_control) + 6 external (marketing, visualizer, memory_vault, barehands, backtalk, fullstack_agent) |
| **LLM** | ✅ Ollama only | Streams responses from local Ollama models (Llama 3.1, Qwen, etc.) with tool-call support |
| **LLM Retry** | ✅ Exponential backoff | 3 retries with backoff on transient errors (connection/timeout/503) |
| **Builtin Skill: System Monitor** | ✅ 6 commands | CPU, memory, disk, GPU, network, processes |
| **Builtin Skill: Code Assistant** | ✅ 3 commands | Analyze files, list functions, find TODOs via AST parsing |
| **Builtin Skill: Memory** | ✅ 3 commands | Remember/recall/forget using ChromaDB vector store |
| **Builtin Skill: Voice Control** | ✅ 4 commands | On/off, test, set language (`/language hi-IN`) |
| **External Skill: Marketing** | ✅ 3 commands | Content creation, campaign ideas, brand voice (file-based, wraps ai-marketing-skills) |
| **External Skill: Fullstack Agent** | ✅ 4 commands | Check toolbox status, run updates, create launchers, setup guide |
| **External Skill: Memory Vault** | ✅ 6 commands | Save/recall/list vault entries, list categories |
| **External Skill: Barehands** | ⚠️ Partial | 6 commands — server launches + HTTP control, but requires barehands server.py installed |
| **External Skill: Backtalk** | ⚠️ Partial | 6 commands — server launches via subprocess, but no HTTP client implemented for talking to the server |
| **External Skill: Visualizer** | ⚠️ Partial | 6 commands — server launches via subprocess, but no HTTP client implemented |
| **MCP Servers** | ✅ All 5 migrated to mcp 2.1.1 | filesystem, terminal, git, memory, web_search |
| **MCP Client** | ✅ Connected | Shared MCPClient between AgentLoop and ToolsScreen; auto-connects on startup |
| **Long-term Memory** | ✅ Vector-based | ChromaDB with cosine similarity; embedding model lazy-loads on first search |
| **Voice: Wake Word** | ✅ Supported | Porcupine (`pvporcupine`) for "Hey JARVIS" hotword detection; MockWakeWord fallback |
| **Voice: TTS** | ✅ Piper + Sarvam | Piper (offline, requires `piper` binary + `.onnx` model); Sarvam AI cloud (requires API key) |
| **Voice: STT** | ✅ Vosk + Sarvam | Vosk (offline, requires model file at `~/.jarvis/voice/`); Sarvam AI cloud (requires API key) |
| **Voice: Language** | ✅ BCP-47 support | Set response language to `en-IN`, `hi-IN`, `ta-IN`, `te-IN`, `bn-IN`, etc. via `/language` command |

### ❌ Not Yet Implemented

| Area | Issue | Impact |
|------|-------|--------|
| **LLM: OpenAI/Anthropic** | `_chat_fallback` returns stub message | Only Ollama works as LLM provider; OpenAI/Anthropic/Llama.cpp settings are accepted but not used |
| **piper-tts binary** | Requires separate `piper` install via `apt`/pip | Piper TTS won't work unless `piper` is on PATH |
| **Vosk model** | Requires manual download of model file | STT won't work until `vosk-model-small-en-us` is at `~/.jarvis/voice/` |
| **Porcupine access** | Requires Picoville AccessKey + `.ppn` keyword file | Wake word won't work until `PORCUPINE_ACCESS_KEY` env var is set and `.ppn` exists |
| **Backtalk HTTP client** | Skill launches server but cannot send messages to it | `backtalk` skill starts server but doesn't communicate via HTTP — commands will return server-not-found |
| **Visualizer HTTP client** | Skill launches server but cannot send prompts to it | Same issue as backtalk |
| **Voice: Hardware testing** | Requires real mic + speakers | Voice pipeline tested only with mock providers, not real hardware |
| **Sarvam AI: Rate limits** | No rate-limit handling in API calls | May fail on burst usage without retry logic |
| **MCP servers as standalone** | Console scripts defined but not verified | `jarvis-mcp-*` scripts should work as stdio servers but need manual testing |

### 🚧 In Development (Planned)

- Llama.cpp support via `llama-cpp-python`
- OpenAI API integration
- Anthropic Claude API integration
- Real-time audio streaming for STT
- Wake word model auto-download
- Voice activity detection (VAD)
- Multi-modal capabilities (image input)

## Requirements

- Python 3.10+
- 8GB+ RAM (for Llama 3.1 8B)
- Microphone & speakers (for voice features)
- Ollama (for LLM) — auto-installed by `jarvis --install`
- Optional: `piper` binary (for offline TTS)
- Optional: Vosk model file (for offline STT)
- Optional: Picoville access key (for wake word)
- Optional: Sarvam AI API key (for cloud TTS/STT)

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

## MCP Servers

- **filesystem** - File operations (sandboxed)
- **terminal** - Safe command execution
- **git** - Git operations
- **memory** - Vector memory access
- **web_search** - DuckDuckGo / API search

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