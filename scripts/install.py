#!/usr/bin/env python3
"""Standalone installer for JARVIS - runs from any directory after pip install."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure the project root is on the path even when running from scripts/
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from jarvis.config.installer import install


async def main() -> None:
    success = await install()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
