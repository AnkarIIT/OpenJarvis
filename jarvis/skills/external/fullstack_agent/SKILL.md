---
name: fullstack_agent
description: "Manage the fullstack-agent installer toolbox: check status, run updates, create launchers, and inspect setup. Use when the user wants to update their agent stack, create desktop shortcuts, or run the fullstack installer."
version: 1.0.0
author: OpenJarvis
---

# Fullstack Agent Skill

Wrapper for `fullstack-agent/`. Exposes installer toolbox commands: status checks, updates, launcher creation, and setup wizard triggers.

## Source
- Installer: `fullstack-agent/fullstack-agent.md`
- Launchers: `fullstack-agent/start.sh`, `start.bat`
- Updater: `fullstack-agent/update.sh`, `update.bat`

## Usage
- Use `fullstack_agent_status` to inspect installed pieces.
- Use `fullstack_agent_update` to pull latest changes.
- Use `fullstack_agent_launchers` to create Desktop shortcuts.
