<p align="center">
  <img src="assets/banner.png" alt="Jarvis Agent" width="100%">
</p>

# Jarvis Agent ☤ v0.21.3
<p align="center">
  <a href="https://github.com/AnkarIIT/OpenJarvis">Jarvis Agent</a> | <a href="https://github.com/AnkarIIT/OpenJarvis">Jarvis Desktop</a>
</p>
<p align="center">
  <a href="https://github.com/AnkarIIT/OpenJarvis"><img src="https://img.shields.io/badge/Docs-GitHub-FFD700?style=for-the-badge" alt="Documentation"></a>
-  <a href="https://discord.gg/NousResearch">Community Discord</a>
  <a href="https://github.com/AnkarIIT/OpenJarvis/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/Lang-中文-red?style=for-the-badge" alt="中文"></a>
  <a href="README.ur-pk.md"><img src="https://img.shields.io/badge/Lang-اردو-green?style=for-the-badge" alt="اردو"></a>
  <a href="README.es.md"><img src="https://img.shields.io/badge/Lang-Español-orange?style=for-the-badge" alt="Español"></a>
</p>

**The self-improving AI agent with a built-in learning loop** — it creates skills from experience, improves them during use, nudges itself to persist knowledge, searches its own past conversations, and builds a deepening model of who you are across sessions. Run it on a $5 VPS, a GPU cluster, or serverless infrastructure that costs nearly nothing when idle. It's not tied to your laptop — talk to it from Telegram while it works on a cloud VM.

Use any model you want — OpenRouter, OpenAI, Anthropic, Gemini, DeepSeek, Qwen, MiniMax, XAI, ZAI, Azure, Bedrock, your own endpoint, and [many others](https://github.com/AnkarIIT/OpenJarvis/wiki/providers). Switch with `jarvis model` — no code changes, no lock-in.

<table>
<tr><td><b>A real terminal interface</b></td><td>Full TUI with multiline editing, slash-command autocomplete, conversation history, interrupt-and-redirect, and streaming tool output. Cyan-themed (#00FFFF accent) with customizable skins — `default`, `ares`, `mono`, `slate`, plus your own YAML skins.</td></tr>
<tr><td><b>Lives where you do</b></td><td>Telegram, Discord, Slack, WhatsApp, Signal, DingTalk, and CLI — all from a single gateway process. Voice memo transcription, cross-platform conversation continuity.</td></tr>
<tr><td><b>A closed learning loop</b></td><td>Agent-curated memory with periodic nudges. Autonomous skill creation after complex tasks. Skills self-improve during use. FTS5 session search with LLM summarization for cross-session recall. <a href="https://github.com/plastic-labs/honcho">Honcho</a> dialectic user modeling. Compatible with the <a href="https://agentskills.io">agentskills.io</a> open standard.</td></tr>
<tr><td><b>Scheduled automations</b></td><td>Built-in cron scheduler with delivery to any platform. Daily reports, nightly backups, weekly audits — all in natural language, running unattended.</td></tr>
<tr><td><b>Delegates and parallelizes</b></td><td>Spawn isolated subagents for parallel workstreams. Write Python scripts that call tools via RPC, collapsing multi-step pipelines into zero-context-cost turns.</td></tr>
<tr><td><b>Runs anywhere, not just your laptop</b></td><td>Seven terminal backends — local, Docker, SSH, Singularity, Modal, Daytona, and Vercel Sandbox. Daytona and Modal offer serverless persistence — your agent's environment hibernates when idle and wakes on demand, costing nearly nothing between sessions. Run it on a $5 VPS or a GPU cluster.</td></tr>
<tr><td><b>Computer use</b></td><td>Built-in browser tool (Browser Use) for web automation — navigate pages, fill forms, click buttons, scrape content. Desktop computer-use via MCP for Linux desktop control with AT-SPI accessibility trees, Wayland/X11 input, screenshots, and compositor window targeting.</td></tr>
<tr><td><b>Kanban & Projects</b></td><td>Visual Kanban boards for task management with dispatchers, swarm workflows, and PR acceptance automation. Projects system for organizing work across sessions.</td></tr>
<tr><td><b>Research-ready</b></td><td>Batch trajectory generation, trajectory compression for training the next generation of tool-calling models. Web search (Firecrawl), image generation (FAL), text-to-speech, all routed through your sub.</td></tr>
<tr><td><b>Multi-profile gateways</b></td><td>Run multiple independent gateways from one install — each profile has its own config, secrets, terminal scope, skills, plugins, cron, and memories. Multiplex mode serves all profiles from one process.</td></tr>
</table>

---

## Quick Install

### Linux, macOS, WSL2, Termux

```bash
curl -fsSL https://raw.githubusercontent.com/AnkarIIT/OpenJarvis/main/install.sh | bash
```

### Windows (native, PowerShell)

> **Heads up:** Native Windows runs Jarvis without WSL — CLI, gateway, TUI, and tools all work natively. If you'd rather use WSL2, the Linux/macOS one-liner above works there too. Found a bug? Please [file issues](https://github.com/AnkarIIT/OpenJarvis/issues).

Run this in PowerShell:

```powershell
iex (irm https://raw.githubusercontent.com/AnkarIIT/OpenJarvis/main/install.ps1)
```

The installer handles everything: uv, Python 3.11, Node.js, ripgrep, ffmpeg, **and a portable Git Bash** (MinGit, unpacked to `%LOCALAPPDATA%\jarvis\git` — no admin required, completely isolated from any system Git install). Jarvis uses this bundled Git Bash to run shell commands.

If you already have Git installed, the installer detects it and uses that instead. Otherwise a ~45MB MinGit download is all you need — it won't touch or interfere with any system Git.

> **Android / Termux:** The tested manual path is documented in the [Termux guide](https://github.com/AnkarIIT/OpenJarvis/wiki/Termux). On Termux, Jarvis installs a curated `.[termux]` extra because the full `.[all]` extra currently pulls Android-incompatible voice dependencies.
>
> **Windows:** Native Windows is fully supported — the PowerShell one-liner above installs everything. If you'd rather use WSL2, the Linux command works there too. Native Windows install lives under `%LOCALAPPDATA%\jarvis`; WSL2 installs under `~/.jarvis` as on Linux.

After installation:

```bash
source ~/.bashrc    # reload shell (or: source ~/.zshrc)
jarvis              # start chatting!
```

### Troubleshooting

#### Windows Defender or antivirus flags `uv.exe` as malware

If your antivirus (Bitdefender, Windows Defender, etc.) quarantines `uv.exe` from the Jarvis `bin` folder (`%LOCALAPPDATA%\jarvis\bin\uv.exe`), this is a **false positive**. The file is Astral's `uv` — the Rust Python package manager Jarvis bundles to manage its Python environment. ML-based antivirus engines commonly flag unsigned Rust binaries that download and install packages.

**To verify your copy is authentic:**

```powershell
# Install GitHub CLI if needed
winget install --id GitHub.cli

# Login to GitHub
gh auth login

# Run verification
$uv = "$env:LOCALAPPDATA\jarvis\bin\uv.exe"
$ver = (& $uv --version).Split(' ')[1]
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$zip = "$env:TEMP\uv.zip"
Invoke-WebRequest "https://github.com/astral-sh/uv/releases/download/$ver/uv-x86_64-pc-windows-msvc.zip" -OutFile $zip -UseBasicParsing
gh attestation verify $zip --repo astral-sh/uv
Expand-Archive $zip "$env:TEMP\uv_x" -Force
(Get-FileHash "$env:TEMP\uv_x\uv.exe").Hash -eq (Get-FileHash $uv).Hash
```

If attestation says "Verification succeeded" and the last line prints `True`, you're good.

**To whitelist Jarvis:**

- **Windows Defender:** Run PowerShell as Admin → `Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\jarvis\bin"`
- **Bitdefender:** Add an exception in the Bitdefender console (Protection > Antivirus > Settings > Manage Exceptions)
- Whitelist the **folder**, not the file hash — Jarvis updates `uv` and the hash changes every version

For more context, see the upstream Astral reports: [astral-sh/uv#13553](https://github.com/astral-sh/uv/issues/13553), [astral-sh/uv#15011](https://github.com/astral-sh/uv/issues/15011), [astral-sh/uv#10079](https://github.com/astral-sh/uv/issues/10079).

---

## Getting Started

```bash
jarvis              # Interactive CLI — start a conversation
jarvis model        # Choose your LLM provider and model
jarvis tools        # Configure which tools are enabled
jarvis config set   # Set individual config values
jarvis config get   # Print individual config values
jarvis gateway      # Start the messaging gateway (Telegram, Discord, etc.)
jarvis setup        # Run the full setup wizard (configures everything at once)
jarvis claw migrate # Migrate from OpenClaw (if coming from OpenClaw)
jarvis update       # Update to the latest version
jarvis doctor       # Diagnose any issues
```

📖 **[Full documentation →](https://github.com/AnkarIIT/OpenJarvis/wiki)**

---

## CLI vs Messaging Quick Reference

Jarvis has two entry points: start the terminal UI with `jarvis`, or run the gateway and talk to it from Telegram, Discord, Slack, WhatsApp, Signal, or Email. Once you're in a conversation, many slash commands are shared across both interfaces.

|| Action                         | CLI                                           | Messaging platforms                                                              |
|| ------------------------------ | --------------------------------------------- | -------------------------------------------------------------------------------- |
|| Start chatting                 | `jarvis`                                      | Run `jarvis gateway setup` + `jarvis gateway start`, then send the bot a message |
|| Start fresh conversation       | `/new` or `/reset`                            | `/new` or `/reset`                                                               |
|| Change model                   | `/model [provider:model]`                     | `/model [provider:model]`                                                        |
|| Set a personality              | `/personality [name]`                         | `/personality [name]`                                                            |
|| Retry or undo the last turn    | `/retry`, `/undo`                             | `/retry`, `/undo`                                                                |
|| Compress context / check usage | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]`                                        |
|| Browse skills                  | `/skills` or `/<skill-name>`                  | `/<skill-name>`                                                                  |
|| Interrupt current work         | `Ctrl+C` or send a new message                | `/stop` or send a new message                                                    |
|| Platform-specific status       | `/platforms`                                  | `/status`, `/sethome`                                                            |

For the full command lists, see the [CLI guide](https://github.com/AnkarIIT/OpenJarvis/wiki/CLI-Usage) and the [Messaging Gateway guide](https://github.com/AnkarIIT/OpenJarvis/wiki/Messaging-Gateway).

---

## Documentation

All documentation lives at **[GitHub Wiki](https://github.com/AnkarIIT/OpenJarvis/wiki)**:

| Section                                                                                             | What's Covered                                             |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Quickstart](https://github.com/AnkarIIT/OpenJarvis/wikigetting-started/quickstart)                 | Install → setup → first conversation in 2 minutes          |
| [CLI Usage](https://github.com/AnkarIIT/OpenJarvis/wiki/CLI-Usage)                              | Commands, keybindings, personalities, sessions             |
| [Configuration](https://github.com/AnkarIIT/OpenJarvis/wikiuser-guide/configuration)                | Config file, providers, models, all options                |
| [Messaging Gateway](https://github.com/AnkarIIT/OpenJarvis/wiki/Messaging-Gateway)                | Telegram, Discord, Slack, WhatsApp, Signal, Home Assistant |
| [Security](https://github.com/AnkarIIT/OpenJarvis/wiki/Security)                          | Command approval, DM pairing, container isolation          |
| [Tools & Toolsets](https://github.com/AnkarIIT/OpenJarvis/wiki/Tools-and-Toolsets)            | 40+ tools, toolset system, terminal backends               |
| [Skills System](https://github.com/AnkarIIT/OpenJarvis/wiki/Skills-System)              | Procedural memory, Skills Hub, creating skills             |
| [Memory](https://github.com/AnkarIIT/OpenJarvis/wiki/Memory)                     | Persistent memory, user profiles, best practices           |
| [MCP Integration](https://github.com/AnkarIIT/OpenJarvis/wiki/MCP-Integration)               | Connect any MCP server for extended capabilities           |
| [Cron Scheduling](https://github.com/AnkarIIT/OpenJarvis/wiki/Cron-Scheduling)              | Scheduled tasks with platform delivery                     |
| [Context Files](https://github.com/AnkarIIT/OpenJarvis/wiki/Context-Files)       | Project context that shapes every conversation             |
| [Architecture](https://github.com/AnkarIIT/OpenJarvis/wiki/Architecture)             | Project structure, agent loop, key classes                 |
| [Contributing](https://github.com/AnkarIIT/OpenJarvis/wiki/Contributing)             | Development setup, PR process, code style                  |
| [CLI Reference](https://github.com/AnkarIIT/OpenJarvis/wiki/CLI-Reference)                  | All commands and flags                                     |
| [Environment Variables](https://github.com/AnkarIIT/OpenJarvis/wiki/Environment-Variables) | Complete env var reference                                 |

---

## Migrating from OpenClaw

If you're coming from OpenClaw, Jarvis can automatically import your settings, memories, skills, and API keys.

**During first-time setup:** The setup wizard (`jarvis setup`) automatically detects `~/.openclaw` and offers to migrate before configuration begins.

**Anytime after install:**

```bash
jarvis claw migrate              # Interactive migration (full preset)
jarvis claw migrate --dry-run    # Preview what would be migrated
jarvis claw migrate --preset user-data   # Migrate without secrets
jarvis claw migrate --overwrite  # Overwrite existing conflicts
```

What gets imported:

- **SOUL.md** — persona file
- **Memories** — MEMORY.md and USER.md entries
- **Skills** — user-created skills → `~/.jarvis/skills/openclaw-imports/`
- **Command allowlist** — approval patterns
- **Messaging settings** — platform configs, allowed users, working directory
- **API keys** — allowlisted secrets (Telegram, OpenRouter, OpenAI, Anthropic, ElevenLabs)
- **TTS assets** — workspace audio files
- **Workspace instructions** — AGENTS.md (with `--workspace-target`)

See `jarvis claw migrate --help` for all options, or use the `openclaw-migration` skill for an interactive agent-guided migration with dry-run previews.

---

## Skin System

Jarvis TUI supports customizable skins — change the look and feel without touching code. Built-in skins:

| Skin    | Description                                                      |
| ------- | ---------------------------------------------------------------- |
| `default` | Classic cyan (#00FFFF) accent on dark background — the Jarvis look |
| `ares`  | Bold, high-contrast theme                                        |
| `mono`  | Minimal monochrome — focused on content                         |
| `slate` | Light, airy pastels — soft hierarchy                            |

Create your own skin as a YAML file in `~/.jarvis/skins/` — define colors, branding, prompt symbol, welcome message, tool prefix, and more. Apply with `/skin <name>` or `jarvis skin set <name>`.

---

## Contributing

We welcome contributions! See the [Contributing Guide](https://github.com/AnkarIIT/OpenJarvis/wiki/Contributing) for development setup, code style, and PR process.

Quick start for contributors — use the standard installer, then work from the
full git checkout it creates at `$JARVIS_HOME/jarvis-agent` (usually
`~/.jarvis/jarvis-agent`). This matches the layout used by `jarvis update`, the
managed venv, lazy dependencies, gateway, and docs tooling.

```bash
curl -fsSL https://raw.githubusercontent.com/AnkarIIT/OpenJarvis/main/install.sh | bash
cd "${JARVIS_HOME:-$HOME/.jarvis}/jarvis-agent"
uv pip install -e ".[all,dev]"
scripts/run_tests.sh
```

Manual clone fallback (for throwaway clones/CI where you intentionally do not
want the managed install layout):

Create the venv outside the cloned source tree — a venv inside the directory
the agent operates from can be wiped by a relative-path command the agent runs
against its own checkout, destroying the running runtime mid-session.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv ~/.jarvis/venvs/jarvis-dev --python 3.11
source ~/.jarvis/venvs/jarvis-dev/bin/activate
uv pip install -e ".[all,dev]"
scripts/run_tests.sh
```

---

## Community

- 💬 [Discord](https://discord.gg/NousResearch)
- 📚 [Skills Hub](https://agentskills.io)
- 🐛 [Issues](https://github.com/AnkarIIT/OpenJarvis/issues)
- 🔌 [computer-use-linux](https://github.com/avifenesh/computer-use-linux) — Linux desktop-control MCP server for Jarvis and other MCP hosts, with AT-SPI accessibility trees, Wayland/X11 input, screenshots, and compositor window targeting.
- 🔌 Community plugins available at [Skills Hub](https://agentskills.io)

---

## License

MIT — see [LICENSE](LICENSE).
