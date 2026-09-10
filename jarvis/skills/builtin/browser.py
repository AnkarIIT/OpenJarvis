from __future__ import annotations

import asyncio
from typing import Any

from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class BrowserSkill:
    name: str = "browser"
    description: str = "Control a web browser: navigate, click, type, screenshot, scroll, and extract page content."
    version: str = "1.0.0"
    author: str = "OpenJarvis"

    async def initialize(self, settings) -> None:
        pass

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="browser_navigate",
                description="Navigate to a URL in the browser",
                handler=self._navigate,
                skill_name=self.name,
            ),
            SkillCommand(
                name="browser_click",
                description="Click an element by CSS selector",
                handler=self._click,
                skill_name=self.name,
            ),
            SkillCommand(
                name="browser_type",
                description="Type text into an element by CSS selector",
                handler=self._type,
                skill_name=self.name,
            ),
            SkillCommand(
                name="browser_screenshot",
                description="Take a screenshot of the current page",
                handler=self._screenshot,
                skill_name=self.name,
            ),
            SkillCommand(
                name="browser_scroll",
                description="Scroll the page up or down",
                handler=self._scroll,
                skill_name=self.name,
            ),
            SkillCommand(
                name="browser_go_back",
                description="Go back to the previous page",
                handler=self._go_back,
                skill_name=self.name,
            ),
            SkillCommand(
                name="browser_get_title",
                description="Get the title of the current page",
                handler=self._get_title,
                skill_name=self.name,
            ),
            SkillCommand(
                name="browser_get_content",
                description="Get the text content of the current page",
                handler=self._get_content,
                skill_name=self.name,
            ),
            SkillCommand(
                name="browser_wait",
                description="Wait for a CSS selector to appear",
                handler=self._wait,
                skill_name=self.name,
            ),
        ]

    async def _navigate(self, url: str) -> str:
        return f"browser_navigate: navigate to {url}"

    async def _click(self, selector: str) -> str:
        return f"browser_click: click {selector}"

    async def _type(self, selector: str, text: str) -> str:
        return f"browser_type: type '{text}' into {selector}"

    async def _screenshot(self, full_page: bool = False) -> str:
        return f"browser_screenshot: capture page (full_page={full_page})"

    async def _scroll(self, direction: str = "down", amount: float = 500) -> str:
        return f"browser_scroll: scroll {direction} by {amount}px"

    async def _go_back(self) -> str:
        return "browser_go_back: go back"

    async def _get_title(self) -> str:
        return "browser_get_title: get page title"

    async def _get_content(self) -> str:
        return "browser_get_content: extract page text"

    async def _wait(self, selector: str, timeout: float = 5000) -> str:
        return f"browser_wait: wait for {selector}"
