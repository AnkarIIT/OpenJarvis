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

## Requirements

- Python 3.10+
- 8GB+ RAM (for Llama 3.1 8B)
- Microphone & speakers (for voice features)

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