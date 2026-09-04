---
name: visualizer
description: Launch and control the ai-visualizer faces from JARVIS. Use when the user wants to see the JARVIS face, switch visualizer modes, run a demo, or control the visualizer state.
version: 1.0.0
author: OpenJarvis
---

# Visualizer Skill

Wrapper for `ai-visualizer/`. Starts the HTTP face server, writes the signal bus files it reads, and exposes commands to switch faces, demo, and stop.

## Source
- Server: `ai-visualizer/server.py`
- Config: `ai-visualizer/ai-visualizer.json`
- Bus files: `.voice_state`, `.voice_waveform`, `.voice_loading_pid`, `.voice_alert`
- Faces: `ai-visualizer/faces/board`, `neural`, `radial`, `rain`

## Usage
- Start the server before driving faces.
- Write bus files to the configured `bus_dir` so the server can serve them.
- Use `--mock` for standalone demos without voice.
