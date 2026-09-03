# OpenJarvis

JARVIS - Just A Rather Very Intelligent System

A terminal-based AI assistant inspired by Iron Man's JARVIS from the Marvel Cinematic Universe. Built with Python, Textual, and local AI models.

## Features

- **Local AI First**: Runs entirely offline with Ollama (Llama 3.1, Qwen, etc.)
- **Terminal UI**: Beautiful TUI built with Textual framework
- **Voice Support**: Offline speech-to-text (Vosk) and text-to-speech (Piper)
- **Wake Word**: "Hey JARVIS" activation (Porcupine)
- **MCP Tools**: Extensible tools via Model Context Protocol
- **Skills System**: Modular skills for system monitoring, code assistance, memory, and more
- **Long-term Memory**: Vector-based memory with ChromaDB
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

| Skill | Description |
|-------|-------------|
| `system_monitor` | CPU, memory, disk, GPU, processes |
| `code_assistant` | Code analysis, TODOs, functions |
| `memory` | Remember, recall, forget |
| `voice_control` | Voice on/off, test |

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