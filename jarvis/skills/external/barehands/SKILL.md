---
name: barehands
description: "Control the barehands air-board: start/stop the hand-tracking server, present cards and media, read board state, and control the assistant ring. Use when the user wants to show something on the board, control the visualizer ring, or manage the barehands server."
version: 1.0.0
author: OpenJarvis
---

# Barehands Skill

Wrapper for `barehands/`. Starts the hand-tracked air-board server, sends stage commands, reads board state, and controls the assistant ring via state files.

## Source
- Server: `barehands/server.py`
- Config: `barehands/barehands.json`
- Ring state: `barehands/state/state`, `state/mood.json`, `state/wave.json`
- Board commands: POST `http://127.0.0.1:8794/cmd` with JSON body
- Allowed actions: `add_card`, `add_img`, `clear`, `reset`, `hand`, `give`, `yank`, `hover`, `scroll_note`, `widget`, `explode`, `assemble`, `present`

## Usage
- Start the server before using board commands.
- Use `barehands_cmd` to stage cards, images, models, and effects.
- Use `barehands_status` to see what's on the board and ring state.
