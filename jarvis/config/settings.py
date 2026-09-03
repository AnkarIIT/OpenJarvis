from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_LLM_")

    provider: Literal["ollama", "llama_cpp", "openai", "anthropic"] = "ollama"
    model: str = "llama3.1:8b"
    base_url: str = "http://localhost:11434"
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120


class MCPSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_MCP_")

    servers: dict[str, dict[str, Any]] = Field(default_factory=dict)


class VoiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_VOICE_")

    enabled: bool = True
    tts_engine: Literal["piper"] = "piper"
    stt_engine: Literal["vosk"] = "vosk"
    wake_word_enabled: bool = True
    wake_word: str = "hey_jarvis"
    tts_voice_model: str = "en_US-lessac-medium"
    stt_model: str = "vosk-model-en-us-0.22"
    sample_rate: int = 16000
    push_to_talk_key: str = "ctrl+space"


class MemorySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_MEMORY_")

    enabled: bool = True
    provider: Literal["chroma"] = "chroma"
    path: str = "~/.jarvis/memory"
    embedding_model: str = "nomic-embed-text"
    collection_name: str = "jarvis_memory"
    max_results: int = 5


class UISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_UI_")

    theme: Literal["jarvis", "dark", "light"] = "jarvis"
    show_tokens: bool = True
    stream: bool = True
    compact_mode: bool = False
    show_voice_indicator: bool = True


class SkillsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_SKILLS_")

    enabled: list[str] = Field(default_factory=lambda: [
        "system_monitor", "code_assistant", "memory", "voice_control"
    ])
    paths: list[str] = Field(default_factory=lambda: [
        "~/.jarvis/skills",
        "./.jarvis/skills"
    ])


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="~/.jarvis/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    version: str = "1.0"
    llm: LLMSettings = Field(default_factory=LLMSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    ui: UISettings = Field(default_factory=UISettings)
    skills: SkillsSettings = Field(default_factory=SkillsSettings)

    @field_validator("llm", "mcp", "voice", "memory", "ui", "skills", mode="before")
    @classmethod
    def parse_nested(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return v
        return {}

    @property
    def config_dir(self) -> Path:
        return Path(os.path.expanduser("~/.jarvis"))

    @property
    def config_file(self) -> Path:
        return self.config_dir / "config.json"

    @property
    def memory_path(self) -> Path:
        return Path(os.path.expanduser(self.memory.path))

    @property
    def skills_paths(self) -> list[Path]:
        return [Path(os.path.expanduser(p)) for p in self.skills.paths]

    def model_dump_json(self, **kwargs: Any) -> str:
        return super().model_dump_json(**kwargs)


def load_settings() -> Settings:
    return Settings()


def save_settings(settings: Settings) -> None:
    settings.config_dir.mkdir(parents=True, exist_ok=True)
    settings.config_file.write_text(settings.model_dump_json(indent=2))