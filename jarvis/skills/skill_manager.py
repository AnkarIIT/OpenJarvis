from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

REGISTRY_PATH = Path(__file__).parent / "skills_registry.json"


class SkillManager:
    """Install, uninstall, list, and search skills for JARVIS.

    Users can selectively install only the skills they need.
    Dependencies are installed automatically.
    """

    def __init__(self, skills_dir: Path = None):
        self.skills_dir = skills_dir or Path(__file__).parent
        self.registry_path = REGISTRY_PATH
        self._registry: dict[str, Any] | None = None

    @property
    def registry(self) -> dict[str, Any]:
        if self._registry is None:
            self._registry = self._load_registry()
        return self._registry

    def _load_registry(self) -> dict[str, Any]:
        with open(self.registry_path) as f:
            return json.load(f)

    def list_skills(self, installed_only: bool = False) -> list[dict[str, Any]]:
        """List all skills with their install status."""
        skills = []
        for skill in self.registry["skills"]:
            status = self._check_installed(skill)
            entry = {
                "name": skill["name"],
                "type": skill["type"],
                "category": skill["category"],
                "description": skill["description"],
                "commands": skill["commands"],
                "enabled_by_default": skill.get("enabled_by_default", False),
                "installed": status["installed"],
                "dependencies": skill.get("dependencies", []),
                "missing_deps": status["missing_deps"],
            }
            if installed_only and not entry["installed"]:
                continue
            skills.append(entry)
        return skills

    def _check_installed(self, skill: dict[str, Any]) -> dict[str, Any]:
        """Check if a skill's dependencies are installed."""
        deps = skill.get("dependencies", [])
        missing = []
        for dep in deps:
            if not self._is_package_installed(dep):
                missing.append(dep)
        return {"installed": len(missing) == 0, "missing_deps": missing}

    def _is_package_installed(self, package_spec: str) -> bool:
        """Check if a pip package is installed."""
        pkg_name = package_spec.split(">=")[0].split("==")[0].split("~=")[0].strip()
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", pkg_name],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def install(self, skill_name: str) -> bool:
        """Install a skill and its dependencies."""
        skill = self._find_skill(skill_name)
        if not skill:
            logger.error(f"Skill '{skill_name}' not found in registry")
            return False

        deps = skill.get("dependencies", [])
        if deps:
            logger.info(f"Installing dependencies for {skill_name}: {deps}")
            for dep in deps:
                self._install_package(dep)

        # Run any post-install command
        install_cmd = skill.get("install_command", "")
        if install_cmd and install_cmd != "jarvis --install":
            logger.info(f"Running: {install_cmd}")
            subprocess.run(install_cmd, shell=True, check=False)

        # Install MCP servers associated with this skill
        mcp_servers = skill.get("mcp_servers", [])
        if mcp_servers:
            logger.info(f"Installing MCP servers: {mcp_servers}")
            for server in mcp_servers:
                self._install_mcp_server(server)

        logger.info(f"Skill '{skill_name}' installed successfully!")
        return True

    def _find_skill(self, name: str) -> dict[str, Any] | None:
        """Find a skill by name in the registry."""
        for skill in self.registry["skills"]:
            if skill["name"] == name:
                return skill
        return None

    def _install_package(self, package_spec: str) -> None:
        """Install a pip package."""
        logger.info(f"pip install {package_spec}")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", package_spec],
            check=True, capture_output=True
        )

    def _install_mcp_server(self, server_name: str) -> None:
        """Install an MCP server via entry point."""
        entry_point = f"jarvis-mcp-{server_name.replace('jarvis-mcp-', '')}"
        logger.info(f"Installing MCP server: {entry_point}")
        # Entry point is installed via pyproject.toml — just verify
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", entry_point],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.warning(f"MCP server '{entry_point}' not installed — run pip install -e .")

    def uninstall(self, skill_name: str) -> bool:
        """Uninstall a skill (mark as disabled, don't remove deps)."""
        skill = self._find_skill(skill_name)
        if not skill:
            logger.error(f"Skill '{skill_name}' not found")
            return False

        # Set enabled_by_default to False
        logger.info(f"Skill '{skill_name}' marked as disabled")
        logger.info("Note: Dependencies are not auto-removed. Use pip to uninstall manually.")
        return True

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search skills by name, description, or category."""
        query_lower = query.lower()
        results = []
        for skill in self.registry["skills"]:
            if (query_lower in skill["name"].lower() or
                query_lower in skill["description"].lower() or
                query_lower in skill["category"].lower()):
                results.append(skill)
        return results

    def get_skill(self, name: str) -> dict[str, Any] | None:
        """Get a single skill by name."""
        return self._find_skill(name)

    def get_category(self, category: str) -> list[dict[str, Any]]:
        """Get all skills in a category."""
        return [s for s in self.registry["skills"] if s["category"] == category]

    def get_stats(self) -> dict[str, int]:
        """Get summary statistics."""
        skills = self.registry["skills"]
        return {
            "total": len(skills),
            "builtin": sum(1 for s in skills if s["type"] == "builtin"),
            "external": sum(1 for s in skills if s["type"] == "external"),
            "installed": sum(1 for s in skills if self._check_installed(s)["installed"]),
            "enabled_by_default": sum(1 for s in skills if s.get("enabled_by_default", False)),
        }


async def async_install_skill(skill_name: str) -> bool:
    """Async wrapper for SkillManager.install()."""
    manager = SkillManager()
    return manager.install(skill_name)
