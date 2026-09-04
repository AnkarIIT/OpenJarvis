from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from jarvis.config.settings import Settings
from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

TEMPLATES_DIR_NAME = "ai-memory-vault/templates"
DEFAULT_VAULT_PATH = Path.home() / "MyVault"


class MemoryVaultSkill:
    name: str = "memory_vault"
    description: str = "Access and manage the AI Memory Vault (Obsidian markdown memory). Initialize vault structure, read/write notes, and prime agent context from vault files."
    version: str = "1.0.0"
    author: str = "OpenJarvis"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings
        self.vault_path: Path | None = None
        self.templates_dir: Path = Path("ai-memory-vault/templates")

    def _resolve_vault(self) -> Path:
        if self.vault_path:
            return self.vault_path
        if self.settings:
            return self.settings.external_memory_vault_dir
        return DEFAULT_VAULT_PATH

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="memory_vault_init",
                description="Initialize the memory vault structure from templates. Creates folders and starter files.",
                handler=self._init,
                skill_name=self.name,
            ),
            SkillCommand(
                name="memory_vault_status",
                description="Check memory vault status: whether it exists, folder count, and key files.",
                handler=self._status,
                skill_name=self.name,
            ),
            SkillCommand(
                name="memory_vault_list",
                description="List vault contents, optionally under a relative path like '01 - Daily Notes'.",
                handler=self._list,
                skill_name=self.name,
            ),
            SkillCommand(
                name="memory_vault_read",
                description="Read a vault markdown file by relative path, e.g. 'VAULT-INDEX.md' or '01 - Daily Notes/2026-01-01.md'.",
                handler=self._read,
                skill_name=self.name,
            ),
            SkillCommand(
                name="memory_vault_write",
                description="Write content to a vault markdown file by relative path. Creates folders as needed.",
                handler=self._write,
                skill_name=self.name,
            ),
            SkillCommand(
                name="memory_vault_prime",
                description="Prime agent context by reading key vault files: VAULT-INDEX.md, Active Priorities, and latest daily note.",
                handler=self._prime,
                skill_name=self.name,
            ),
        ]

    def _resolve_templates_dir(self) -> Path:
        if self.settings is not None:
            return self.settings.project_root / "ai-memory-vault" / "templates"
        return Path(__file__).resolve().parents[4] / "ai-memory-vault" / "templates"

    async def initialize(self, settings: Any) -> None:
        self.settings = settings
        self.vault_path = self._resolve_vault()
        self.templates_dir = self._resolve_templates_dir()

    async def _init(self, path: str = "") -> str:
        target = Path(os.path.expanduser(path)) if path else self._resolve_vault()
        target.mkdir(parents=True, exist_ok=True)

        folders = [
            "00 - Inbox",
            "01 - Daily Notes",
            "02 - Projects",
            "03 - Personal",
            "04 - Archive",
            "05 - Resources",
        ]
        for folder in folders:
            (target / folder).mkdir(parents=True, exist_ok=True)

        copied = []
        for template_name in ["VAULT-INDEX.md", "DAILY-NOTE.md", "MEMORY.md", "CLAUDE.md"]:
            src = self.templates_dir / template_name
            dst = target / template_name
            if src.exists() and not dst.exists():
                dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                copied.append(template_name)

        active = target / "Active Priorities.md"
        if not active.exists():
            active.write_text(
                "# Active Priorities\n\n- [ ] Add priorities here as they come up.\n",
                encoding="utf-8",
            )
            copied.append("Active Priorities.md")

        lines = [f"Memory vault initialized at: {target}", f"Folders: {', '.join(folders)}"]
        if copied:
            lines.append(f"Templates copied: {', '.join(copied)}")
        else:
            lines.append("No templates copied (target already had files).")
        return "\n".join(lines)

    async def _status(self) -> str:
        vault = self._resolve_vault()
        if not vault.exists() or not vault.is_dir():
            return f"Vault not found at: {vault}"

        folders = [p.name for p in vault.iterdir() if p.is_dir()]
        files = [p.name for p in vault.iterdir() if p.is_file() and p.suffix == ".md"]
        key_files = ["VAULT-INDEX.md", "Active Priorities.md", "CLAUDE.md", "MEMORY.md", "DAILY-NOTE.md"]
        missing = [f for f in key_files if f not in files and not (vault / f).exists()]

        lines = [
            f"Vault: {vault}",
            f"Folders: {len(folders)} ({', '.join(sorted(folders))})",
            f"Markdown files: {len(files)}",
        ]
        if missing:
            lines.append(f"Missing key files: {', '.join(missing)}")
        else:
            lines.append("Key files: present")
        return "\n".join(lines)

    async def _list(self, subpath: str = "") -> str:
        vault = self._resolve_vault()
        target = (vault / subpath).resolve() if subpath else vault
        if not target.exists() or not target.is_dir():
            return f"Path not found: {target}"

        dirs = sorted([p.name for p in target.iterdir() if p.is_dir()])
        files = sorted([p.name for p in target.iterdir() if p.is_file()])
        lines = [f"Vault listing: {target}"]
        if dirs:
            lines.append("Directories:")
            for d in dirs:
                lines.append(f"  {d}/")
        if files:
            lines.append("Files:")
            for f in files:
                lines.append(f"  {f}")
        if not dirs and not files:
            lines.append("(empty)")
        return "\n".join(lines)

    async def _read(self, relpath: str = "VAULT-INDEX.md") -> str:
        vault = self._resolve_vault()
        target = (vault / relpath).resolve()
        if not target.exists() or not target.is_file():
            return f"File not found: {target}"
        try:
            text = target.read_text(encoding="utf-8")
            if len(text) > 12000:
                return text[:12000] + "\n\n... [truncated for context priming]"
            return text
        except Exception as e:
            logger.error("Failed to read vault file %s: %s", target, e)
            return f"Failed to read file: {e}"

    async def _write(self, relpath: str = "", content: str = "") -> str:
        if not relpath:
            return "Missing required argument: relpath"
        vault = self._resolve_vault()
        target = (vault / relpath).resolve()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"Wrote vault file: {target}"
        except Exception as e:
            logger.error("Failed to write vault file %s: %s", target, e)
            return f"Failed to write file: {e}"

    async def _prime(self) -> str:
        vault = self._resolve_vault()
        if not vault.exists():
            return f"Vault not found at: {vault}"

        files_to_read = ["VAULT-INDEX.md", "Active Priorities.md"]
        latest_daily = self._find_latest_daily_note(vault)
        if latest_daily:
            files_to_read.append(str(latest_daily.relative_to(vault)))

        loaded = []
        for rel in files_to_read:
            text = await self._read(rel)
            if text.startswith("File not found") or text.startswith("Failed to read"):
                continue
            loaded.append(f"--- {rel} ---\n{text}")

        if not loaded:
            return "No vault files were available to prime from."
        return "\n\n".join(loaded)

    def _find_latest_daily_note(self, vault: Path) -> Path | None:
        daily_root = vault / "01 - Daily Notes"
        if not daily_root.exists():
            return None
        candidates = list(daily_root.rglob("*.md"))
        if not candidates:
            return None
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for candidate in candidates:
            if candidate.name.lower() != "daily note template.md":
                return candidate
        return candidates[0]
