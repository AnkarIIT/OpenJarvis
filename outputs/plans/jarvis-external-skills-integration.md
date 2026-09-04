# JARVIS External Skills Integration Plan

## Objective
Wrap the existing sub-projects in `C:\codes\jarvis\` as JARVIS skills without modifying their original code. JARVIS should be able to launch, control, and use these tools through its existing skill system.

---

## 1. Current State Assessment

### 1.1 JARVIS Skill System (already working)
- **Discovery**: `jarvis/skills/loader.py` scans `skills.paths` for folders with `SKILL.md` or `skill.yaml`
- **Registration**: `jarvis/skills/registry.py` registers `SkillCommand(name, description, handler, skill_name)`
- **Execution**: Handlers are `async` callables that can do anything
- **Built-in skills**: `jarvis/skills/builtin/` — `system_monitor` (functional), `code_assistant` (stub), `memory` (stub), `voice_control` (stub)
- **External skill paths**: `~/.jarvis/skills/` and `./.jarvis/skills/` (from `SkillsSettings`)

### 1.2 Sub-projects (as-is, untouched)
| Folder | Type | Entry point | Config |
|---|---|---|---|
| `ai-marketing-skills/` | Markdown skill pack | N/A (content only) | `jaredrhod-marketing/` contains `SKILL.md` |
| `ai-visualizer/` | Python HTTP server | `server.py` | `ai-visualizer.json` |
| `barehands/` | Python HTTP server + browser | `server.py`, `stage.html` | `barehands.json` |
| `backtalk/` | Python voice pipeline | `backtalk/main.py` | `backtalk.json` |
| `ai-memory-vault/` | Markdown vault + templates | N/A (content + templates) | `templates/` |
| `fullstack-agent/` | Shell installer scripts | `start.sh`, `install.sh` | N/A |

---

## 2. Architecture Decision

### 2.1 Wrapper Pattern
Each sub-project gets a **thin wrapper skill** in:
```
jarvis/skills/external/<skill_name>/
├── SKILL.md          # Metadata: name, description, version, commands
└── skill.py          # Async handlers that orchestrate the sub-project
```

The wrapper:
- **Never modifies** the original sub-project code
- **Never moves** the original sub-project code
- Uses **subprocess** or **local HTTP/API calls** to drive the sub-project
- Reads/writes the sub-project's own config files when needed

### 2.2 Why subprocess over import?
- Sub-projects are standalone apps with their own configs, dependencies, and runtimes
- Importing them risks dependency conflicts and lifecycle issues
- Subprocess isolation keeps JARVIS stable if a sub-project crashes
- Sub-projects can still be run independently for development

### 2.3 Communication Channels
| Sub-project | Channel | Details |
|---|---|---|
| `ai-visualizer` | Subprocess + signal files | Run `server.py`, write `.voice_state` etc. to its `bus_dir` |
| `barehands` | Subprocess + HTTP + shell | Run `server.py`, call `bin/board.sh`, read `state/state` |
| `ai-marketing-skills` | File read + prompt injection | Read markdown files, inject into LLM context |
| `ai-memory-vault` | File I/O | Read/write markdown vault, optional ChromaDB sync |
| `backtalk` | Subprocess (future) | Run voice pipeline, pipe audio — **deferred** |
| `fullstack-agent` | Shell execution | Run installer scripts — **low priority** |

---

## 3. Configuration Changes

### 3.1 Extend `jarvis/config/settings.py`
Add an `ExternalSkillsSettings` block:

```python
class ExternalSkillsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_EXT_")

    # Absolute or relative paths to sub-projects
    visualizer_path: str = "./ai-visualizer"
    barehands_path: str = "./barehands"
    marketing_path: str = "./ai-marketing-skills"
    memory_vault_path: str = "./ai-memory-vault"
    backtalk_path: str = "./backtalk"
    fullstack_agent_path: str = "./fullstack-agent"

    # Runtime config
    visualizer_port: int = 8790
    barehands_port: int = 8794
    visualizer_face: str = "circuit"
    visualizer_mock: bool = False
```

### 3.2 Path resolution
- Settings should resolve relative paths from the **project root** (`C:\codes\jarvis\`)
- Fallback to absolute paths if the relative path doesn't exist
- This lets JARVIS work whether deployed as a package or from source

---

## 4. Skill-by-Skill Implementation Plan

### Phase 1: Low Effort, High Value (Week 1)

#### Skill 1: `marketing` (from `ai-marketing-skills/`)
**Goal**: Expose marketing copywriting templates and frameworks as JARVIS skills.

**Files**:
```
jarvis/skills/external/marketing/
├── SKILL.md
└── skill.py
```

**Commands**:
| Command | Description |
|---|---|
| `marketing_list_categories` | List available skill categories |
| `marketing_load_category` | Load a category (e.g., `marketing-copywriting`) |
| `marketing_generate` | Generate marketing content using a loaded framework |

**Implementation**:
- Read markdown files from `ai-marketing-skills/jaredrhod-marketing/`
- Inject content into the LLM prompt as context
- No subprocess needed — pure file I/O + prompt engineering

**Risk**: Low. No execution, just reading and prompting.

---

#### Skill 2: `visualizer` (from `ai-visualizer/`)
**Goal**: Launch and control the AI visualizer from JARVIS.

**Files**:
```
jarvis/skills/external/visualizer/
├── SKILL.md
└── skill.py
```

**Commands**:
| Command | Description |
|---|---|
| `visualizer_start` | Start `server.py` as subprocess |
| `visualizer_stop` | Kill the server subprocess |
| `visualizer_status` | Check if server is running |
| `visualizer_demo` | Trigger demo mode (`?demo=1`) |
| `visualizer_set_face` | Switch face (circuit, radial, matrix, neural) |

**Implementation**:
- Spawn `python server.py` as an `asyncio.subprocess`
- Track PID in skill state
- Signal files (`.voice_state`, `.voice_waveform`, `.voice_loading_pid`) written to `ai-visualizer/` for the visualizer to read
- Read visualizer's state via its local HTTP endpoint if needed

**Risk**: Low. Subprocess management is straightforward. Signal bus is already documented.

---

### Phase 2: Medium Effort (Week 2)

#### Skill 3: `memory_vault` (from `ai-memory-vault/`)
**Goal**: Add file-based markdown memory alongside ChromaDB.

**Files**:
```
jarvis/skills/external/memory_vault/
├── SKILL.md
└── skill.py
```

**Commands**:
| Command | Description |
|---|---|
| `vault_write` | Write a note to the vault |
| `vault_search` | Search vault by filename or content |
| `vault_list` | List recent notes |
| `vault_sync` | Sync vault entries to/from ChromaDB |

**Implementation**:
- Vault is just a folder of `.md` files
- Write: create timestamped markdown file in vault directory
- Search: `grep` or Python `pathlib` scan
- Sync: optional — index vault files into ChromaDB for semantic search

**Risk**: Low-medium. File I/O is simple. Sync logic needs care to avoid duplicates.

---

#### Skill 4: `barehands` (from `barehands/`)
**Goal**: Control the barehands board from JARVIS.

**Files**:
```
jarvis/skills/external/barehands/
├── SKILL.md
└── skill.py
```

**Commands**:
| Command | Description |
|---|---|
| `barehands_start` | Start `server.py` |
| `barehands_stop` | Stop server |
| `barehands_board_add_card` | Add a card to the board via `board.sh` |
| `barehands_board_state` | Read current board state |
| `barehands_gesture_help` | List available gestures |

**Implementation**:
- Spawn `server.py` as subprocess
- Execute `bin/board.sh` with JSON payloads for board commands
- Read `state/state` file for current board state
- Open browser to `stage.html` if needed

**Risk**: Medium. Requires webcam + Chrome. Board commands are well-documented but need testing.

---

### Phase 3: Higher Effort / Deferred (Week 3+)

#### Skill 5: `voice_line` (from `backtalk/`)
**Goal**: Use backtalk's voice pipeline as JARVIS's voice backend.

**Status**: **DEFERRED**
**Reason**: 
- backtalk is tightly coupled to Claude Code's agent SDK
- JARVIS already has its own voice pipeline (Vosk + Piper + Porcupine)
- Integration would require significant refactoring of backtalk's audio loop
- Better approach: migrate individual components (faster-whisper, Kokoro) into JARVIS's existing pipeline

**Future path**: Replace JARVIS's current STT/TTS with backtalk's components, not wrap the whole app.

---

#### Skill 6: `fullstack_setup` (from `fullstack-agent/`)
**Goal**: One-command setup of the full stack.

**Status**: **LOW PRIORITY**
**Reason**: 
- Mostly a convenience wrapper around shell scripts
- JARVIS already has its own installer
- Value is low compared to other skills

**Future path**: If needed, expose as a single command that runs the setup wizard.

---

## 5. Skill Registration Changes

### 5.1 Current: `jarvis/skills/registry.py`
Currently loads builtin skills only:
```python
async def _load_builtin_skills(self) -> None:
    from jarvis.skills.builtin.system_monitor import SystemMonitorSkill
    ...
```

### 5.2 Needed: Auto-discover external skills
Add external skill discovery to the registry initialization:

```python
async def initialize(self) -> None:
    await self.loader.discover_skills()  # Already discovers external skills
    await self._load_builtin_skills()
```

The `SkillLoader` already scans `skills.paths` (which includes `~/.jarvis/skills/` and `./.jarvis/skills/`). We just need to:
1. Add `jarvis/skills/external/` to the default `skills.paths`
2. Ensure each external skill folder has a `SKILL.md` with proper frontmatter
3. Each `skill.py` exposes a class with `get_commands()` returning `SkillCommand` list

---

## 6. Testing Strategy

### 6.1 Per-skill tests
Each skill wrapper should have:
- **Unit tests**: Mock subprocess calls, test command routing
- **Integration tests**: Run the actual sub-project in test mode, verify commands work
- **Failure tests**: Sub-project not installed, subprocess crashes, config missing

### 6.2 System tests
- Install JARVIS fresh, verify all skills load
- Run `jarvis doctor`, verify external skill status
- Test skill commands from TUI command palette

### 6.3 Manual testing checklist
- [ ] `marketing_list_categories` returns categories
- [ ] `visualizer_start` launches server, `visualizer_demo` shows animation
- [ ] `vault_write` creates a note, `vault_search` finds it
- [ ] `barehands_board_add_card` adds a card to the board

---

## 7. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Sub-project dependencies missing | Medium | High | Each skill checks for its dependencies at init, reports status in `jarvis doctor` |
| Subprocess leaks (zombie processes) | Medium | Medium | Track PIDs, implement proper cleanup in skill `__aexit__` or app shutdown |
| Port conflicts | Low | Medium | Configurable ports, check availability before launch |
| Path resolution issues on different OS | Medium | Medium | Use `pathlib`, resolve from project root, fallback to absolute |
| Sub-project API changes | Low | Medium | Pin sub-project versions, or use git submodules |
| Voice pipeline conflicts (backtalk vs JARVIS) | High | High | **Defer backtalk integration** — not wrapping it, just using its components later |

---

## 8. Implementation Order

```
Week 1:
  Day 1-2: marketing skill (low effort, test pattern)
  Day 3-4: visualizer skill (subprocess pattern, signal bus)

Week 2:
  Day 1-2: memory_vault skill (file I/O pattern)
  Day 3-4: barehands skill (subprocess + HTTP + shell pattern)

Week 3:
  Day 1-2: Testing, bug fixes, edge cases
  Day 3-4: Documentation, README updates, demo

Deferred:
  backtalk → component migration instead of wrapping
  fullstack-agent → low priority, revisit if needed
```

---

## 9. File Structure (Final)

```
C:\codes\jarvis\
├── jarvis/
│   └── skills/
│       ├── builtin/           # Existing built-in skills
│       │   ├── system_monitor.py
│       │   ├── code_assistant.py
│       │   ├── memory.py
│       │   └── voice_control.py
│       ├── external/          # NEW: Wrapper skills
│       │   ├── marketing/
│       │   │   ├── SKILL.md
│       │   │   └── skill.py
│       │   ├── visualizer/
│       │   │   ├── SKILL.md
│       │   │   └── skill.py
│       │   ├── memory_vault/
│       │   │   ├── SKILL.md
│       │   │   └── skill.py
│       │   └── barehands/
│       │       ├── SKILL.md
│       │       └── skill.py
│       ├── loader.py
│       └── registry.py
├── ai-marketing-skills/       # Untouched
├── ai-visualizer/             # Untouched
├── barehands/                 # Untouched
├── backtalk/                  # Untouched (deferred)
├── ai-memory-vault/           # Untouched
└── fullstack-agent/           # Untouched (deferred)
```

---

## 10. Success Criteria
1. All 4 implemented skills load automatically on JARVIS startup
2. `jarvis doctor` shows external skill status
3. Each skill's commands are callable from the TUI command palette
4. Sub-projects remain runnable independently (no modifications)
5. No regression in existing JARVIS functionality

---

*Plan created: 2025*
*Status: Ready for implementation*
