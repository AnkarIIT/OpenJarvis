---
name: memory_vault
description: Access and manage the AI Memory Vault (Obsidian markdown memory). Use when the user wants to read their vault, write notes, initialize vault structure, prime context from memory, or check vault status.
version: 1.0.0
author: OpenJarvis
---

# Memory Vault Skill

Wrapper for `ai-memory-vault/`. Reads and writes markdown files in an Obsidian vault, initializes vault structure from templates, and primes the agent with vault context.

## Source
- Build script: `ai-memory-vault/ai-memory-vault.md`
- Templates: `ai-memory-vault/templates/`
- Vault root: configured via `external.memory_vault_path` (default `~/MyVault`)

## Usage
- Use `memory_vault_init` to create vault structure from templates.
- Use `memory_vault_read` / `memory_vault_write` to access notes.
- Use `memory_vault_prime` to load vault context before a task.
