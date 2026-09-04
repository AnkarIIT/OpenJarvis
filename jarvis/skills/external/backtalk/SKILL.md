---
name: backtalk
description: "Control the backtalk voice loop: start/stop the voice server, set ring state, manage config, and check voice status. Use when the user wants to talk to their agent, test the voice, or manage backtalk."
version: 1.0.0
author: OpenJarvis
---

# Backtalk Skill

Wrapper for `backtalk/`. Starts the voice loop subprocess, manages signal state files, and exposes basic voice control commands.

## Source
- Main: `backtalk/backtalk/main.py`
- Config: `backtalk/backtalk.json`
- State: `backtalk/state/state`, `state/mood.json`, `state/wave.json`
- Signals: `.voice_state`, `.voice_waveform`, `.voice_loading_pid`, `.voice_alert`

## Usage
- Start the voice loop before using voice commands.
- Use `backtalk_set_state` to control the ring/face state.
- Use `backtalk_status` to check if voice is running.
