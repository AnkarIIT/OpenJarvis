from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from typing import Any, Awaitable

from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class CodeAssistantSkill:
    name: str = "code_assistant"
    description: str = "Code analysis, editing, and development assistance"

    async def initialize(self, settings) -> None:
        pass

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="analyze_code",
                description="Analyze code structure and quality for a Python file or directory",
                handler=self._analyze_code,
                skill_name=self.name,
            ),
            SkillCommand(
                name="find_todos",
                description="Find TODO/FIXME comments in codebase",
                handler=self._find_todos,
                skill_name=self.name,
            ),
            SkillCommand(
                name="list_functions",
                description="List functions in a Python file",
                handler=self._list_functions,
                skill_name=self.name,
            ),
        ]

    async def _analyze_code(self, path: str) -> str:
        target = Path(path).expanduser().resolve()
        if not target.exists():
            return f"Path not found: {target}"

        python_files = self._collect_python_files(target)
        if not python_files:
            return f"No Python files found under: {target}"

        total_functions = 0
        total_classes = 0
        total_lines = 0
        samples: list[str] = []

        for file_path in python_files[:20]:
            try:
                source = file_path.read_text(encoding="utf-8", errors="replace")
                total_lines += len(source.splitlines())
                tree = ast.parse(source)
                functions = sum(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))
                classes = sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
                total_functions += functions
                total_classes += classes
                if functions or classes:
                    samples.append(
                        f"- {file_path.relative_to(target.parent if target.is_file() else target)}: "
                        f"{functions} functions, {classes} classes"
                    )
            except SyntaxError as e:
                samples.append(f"- {file_path}: syntax error: {e}")
            except Exception as e:
                logger.error(f"Failed to analyze {file_path}: {e}")

        header = (
            f"Code analysis for: {target}\n"
            f"Files scanned: {len(python_files)}\n"
            f"Total lines: {total_lines}\n"
            f"Functions: {total_functions}\n"
            f"Classes: {total_classes}\n"
        )
        if samples:
            header += "\nBreakdown:\n" + "\n".join(samples[:20])
        return header

    async def _find_todos(self, path: str = ".") -> str:
        target = Path(path).expanduser().resolve()
        if not target.exists():
            return f"Path not found: {target}"

        markers = ("TODO", "FIXME", "HACK", "XXX")
        hits: list[str] = []

        python_files = self._collect_python_files(target)
        for file_path in python_files[:50]:
            try:
                source = file_path.read_text(encoding="utf-8", errors="replace")
                for lineno, line in enumerate(source.splitlines(), 1):
                    stripped = line.strip()
                    if any(stripped.startswith(m) for m in markers):
                        hits.append(f"{file_path}:{lineno}: {stripped}")
            except Exception as e:
                logger.error(f"Failed scanning {file_path}: {e}")

        if not hits:
            return f"No TODO/FIXME comments found under: {target}"

        return (
            f"Found {len(hits)} TODO comments under {target}:\n"
            + "\n".join(hits[:100])
        )

    async def _list_functions(self, file: str) -> str:
        target = Path(file).expanduser().resolve()
        if not target.exists():
            return f"File not found: {target}"

        try:
            source = target.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except SyntaxError as e:
            return f"Syntax error in {target}: {e}"
        except Exception as e:
            return f"Failed to read {target}: {e}"

        functions: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                args = [a.arg for a in node.args.args]
                functions.append(
                    f"- {node.name}({', '.join(args)}) at line {node.lineno}"
                )

        if not functions:
            return f"No functions found in {target}"

        return (
            f"Functions in {target}:\n"
            + "\n".join(functions[:200])
        )

    def _collect_python_files(self, target: Path) -> list[Path]:
        if target.is_file():
            return [target] if target.suffix == ".py" else []
        files: list[Path] = []
        for root, dirs, filenames in os.walk(target):
            # Skip hidden and common noise directories
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d not in {"__pycache__", "node_modules", ".venv", "venv", "dist", "build"}
            ]
            for filename in filenames:
                if filename.endswith(".py"):
                    files.append(Path(root) / filename)
        return sorted(files)
