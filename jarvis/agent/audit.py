from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_SENSITIVE_KEYS = {"api_key", "authorization", "password", "secret", "token"}


def _safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if str(key).lower() in _SENSITIVE_KEYS else _safe_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_safe_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class AuditLogger:
    def __init__(self, path: Path):
        self.path = path

    def record(
        self,
        *,
        task_id: str | None,
        tool: str,
        source: str,
        status: str,
        arguments: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "tool": tool,
            "source": source,
            "status": status,
            "arguments": _safe_value(arguments or {}),
            "error": error,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        """Read all audit log entries (JSONL)."""
        if not self.path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries
