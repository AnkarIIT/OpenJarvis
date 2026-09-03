#!/usr/bin/env python3
"""Standalone installer for JARVIS"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jarvis.config.installer import install


async def main():
    success = await install()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())