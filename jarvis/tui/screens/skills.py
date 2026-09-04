from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Static, Button, Label, ListView, ListItem
from textual.reactive import reactive

from jarvis.config.settings import Settings
from jarvis.skills.registry import SkillRegistry, Skill


class SkillsScreen(Screen):
    BINDINGS = [
        ("escape", "back", "Back"),
        ("enter", "toggle_skill", "Toggle"),
    ]

    def __init__(self, settings: Settings, skill_registry: SkillRegistry):
        super().__init__()
        self.settings = settings
        self.skill_registry = skill_registry
        self.skills: list[Skill] = []
        self.selected_index = -1

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
        self.skills = await self.skill_registry.loader.discover_skills()
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
        item = event.item
        if item and item.id and item.id.startswith("skill-"):
            name = item.id.replace("skill-", "", 1)
            for idx, skill in enumerate(self.skills):
                if skill.name == name:
                    self.selected_index = idx
                    break

    def action_toggle_skill(self) -> None:
        if self.selected_index < 0 or self.selected_index >= len(self.skills):
            return
        skill = self.skills[self.selected_index]

        async def _toggle() -> None:
            if skill.enabled:
                ok = await self.skill_registry.disable_skill(skill.name)
            else:
                ok = await self.skill_registry.enable_skill(skill.name)

            if ok:
                skill.enabled = not skill.enabled
                await self._load_skills()
                list_view = self.query_one("#skills-list", ListView)
                if self.selected_index < list_view.children_count:
                    list_view.index = self.selected_index

        self.run_worker(_toggle())

    def action_back(self) -> None:
        self.app.switch_screen("chat")