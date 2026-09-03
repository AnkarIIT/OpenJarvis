from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Static, Button, Label, ListView, ListItem
from textual.reactive import reactive

from jarvis.config.settings import Settings
from jarvis.skills.loader import SkillLoader


class SkillsScreen(Screen):
    BINDINGS = [
        ("escape", "back", "Back"),
        ("enter", "toggle_skill", "Toggle"),
    ]

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.loader = SkillLoader(settings)
        self.skills = []

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Static("Skills Management", id="skills-title"),
                Horizontal(
                    Button("Refresh", id="refresh-btn"),
                    Button("Install Skill", id="install-btn", variant="primary"),
                    id="skills-actions",
                ),
                ListView(id="skills-list"),
                id="skills-container",
            )
        )

    async def on_mount(self) -> None:
        await self._load_skills()

    async def _load_skills(self) -> None:
        self.skills = await self.loader.discover_skills()
        list_view = self.query_one("#skills-list", ListView)
        await list_view.clear()

        for skill in self.skills:
            status = "✓" if skill.enabled else "✗"
            item = ListItem(
                Horizontal(
                    Label(f"{status} {skill.name}", classes="skill-name"),
                    Label(skill.description, classes="skill-desc"),
                    classes="skill-item",
                ),
                id=f"skill-{skill.name}",
            )
            await list_view.append(item)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        pass

    def action_back(self) -> None:
        self.app.switch_screen("chat")

    def action_toggle_skill(self) -> None:
        pass