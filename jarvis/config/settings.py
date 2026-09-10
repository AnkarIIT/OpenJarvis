from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_LLM_")

    provider: Literal["auto", "ollama", "llama_cpp", "lm_studio", "localai", "openai", "anthropic"] = "auto"
    model: str = "llama3.1:8b"
    model_path: str | None = None  # Path to GGUF model for llama_cpp provider
    base_url: str = "http://localhost:11434"
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120
    auto_detect: bool = True  # When provider is "auto", probe available providers in priority order


class MCPSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_MCP_")

    servers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    auto_discover: bool = True  # Auto-discover MCP servers from built-in implementations


class VoiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_VOICE_")

    enabled: bool = True
    tts_engine: Literal["piper", "sarvam"] = "piper"
    stt_engine: Literal["vosk", "sarvam", "whisper"] = "vosk"
    wake_word_enabled: bool = True
    wake_word: str = "hey_jarvis"
    wake_word_engine: Literal["auto", "openwakeword", "porcupine"] = "auto"
    tts_voice_model: str = "en_US-lessac-medium"
    stt_model: str = "vosk-model-small-en-us-0.15"
    sample_rate: int = 16000
    push_to_talk_key: str = "ctrl+space"
    sarvam_api_key: str = ""  # Set via JARVIS_VOICE_SARVAM_API_KEY env var
    sarvam_tts_model: Literal["bulbul:v3", "bulbul:v2"] = "bulbul:v3"
    sarvam_stt_model: Literal["saaras:v3", "saaras:v4"] = "saaras:v3"
    sarvam_tts_speaker: str = "shubh"
    sarvam_tts_pace: float = 1.0
    sarvam_tts_temperature: float = 0.6
    language: str = "en-IN"  # BCP-47 language code for both TTS and STT output
    language_detection: bool = True  # Auto-detect spoken language for response


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
            "system_monitor", "code_assistant", "memory", "voice_control",
            "predictive", "autonomous", "traffic_camera", "multisensory",
            "instant_learning", "emotional",
            "marketing", "visualizer", "memory_vault", "barehands", "backtalk", "fullstack_agent"
        ])
    paths: list[str] = Field(default_factory=lambda: [])  # Computed dynamically


class ExternalSkillsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_EXT_")

    visualizer_path: str = "./ai-visualizer"
    visualizer_bus_dir: str = "~/.jarvis/visualizer_bus"
    visualizer_port: int = 8790
    visualizer_default_face: str = "board"
    memory_vault_path: str = "~/MyVault"
    barehands_path: str = "./barehands"
    barehands_state_dir: str = ""
    barehands_port: int = 8794
    backtalk_path: str = "./backtalk"
    backtalk_state_dir: str = ""
    backtalk_port: int = 8795
    fullstack_agent_path: str = "./fullstack-agent"


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
    external: ExternalSkillsSettings = Field(default_factory=ExternalSkillsSettings)

    @field_validator("llm", "mcp", "voice", "memory", "ui", "skills", "external", mode="before")
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
        """Return resolved absolute paths for skill discovery.

        Uses dynamically computed paths that work both in dev and installed mode.
        """
        paths: list[Path] = []
        proj_root = Path(__file__).resolve().parent.parent.parent
        candidates = [
            Path.home() / ".jarvis" / "skills",
            Path.cwd() / ".jarvis" / "skills",
            proj_root / "jarvis" / "skills" / "external",
            proj_root / "skills",
        ]
        for p in candidates:
            if p.exists():
                paths.append(p.resolve())
        # Always include CWD fallback
        if not any(p == Path.cwd() / "skills" for p in paths):
            if (Path.cwd() / "skills").exists():
                paths.append(Path.cwd() / "skills")
        return paths

    @property
    def external_visualizer_dir(self) -> Path:
        p = Path(os.path.expanduser(self.external.visualizer_path))
        if not p.is_absolute():
            candidate = Path(__file__).resolve().parent.parent.parent / self.external.visualizer_path
            if candidate.exists():
                return candidate.resolve()
            return Path.cwd() / self.external.visualizer_path
        return p

    @property
    def external_visualizer_bus_dir(self) -> Path:
        return Path(os.path.expanduser(self.external.visualizer_bus_dir))

    @property
    def external_memory_vault_dir(self) -> Path:
        return Path(os.path.expanduser(self.external.memory_vault_path))

    @property
    def external_barehands_dir(self) -> Path:
        p = Path(os.path.expanduser(self.external.barehands_path))
        if not p.is_absolute():
            candidate = Path(__file__).resolve().parent.parent.parent / self.external.barehands_path
            if candidate.exists():
                return candidate.resolve()
            return Path.cwd() / self.external.barehands_path
        return p

    @property
    def external_barehands_state_dir(self) -> Path:
        raw = self.external.barehands_state_dir
        if raw:
            return Path(os.path.expanduser(raw))
        return self.external_barehands_dir / "state"

    @property
    def external_backtalk_dir(self) -> Path:
        p = Path(os.path.expanduser(self.external.backtalk_path))
        if not p.is_absolute():
            candidate = Path(__file__).resolve().parent.parent.parent / self.external.backtalk_path
            if candidate.exists():
                return candidate.resolve()
            return Path.cwd() / self.external.backtalk_path
        return p

    @property
    def external_backtalk_state_dir(self) -> Path:
        raw = self.external.backtalk_state_dir
        if raw:
            return Path(os.path.expanduser(raw))
        return self.external_backtalk_dir / "state"

    @property
    def external_fullstack_agent_dir(self) -> Path:
        p = Path(os.path.expanduser(self.external.fullstack_agent_path))
        if not p.is_absolute():
            candidate = Path(__file__).resolve().parent.parent.parent / self.external.fullstack_agent_path
            if candidate.exists():
                return candidate.resolve()
            return Path.cwd() / self.external.fullstack_agent_path
        return p

    @property
    def project_root(self) -> Path:
        """Best-effort project root relative to this settings file.

        Falls back to CWD when the package is installed and the source tree
        is not available.
        """
        candidate = Path(__file__).resolve().parent.parent.parent
        if (candidate / "pyproject.toml").exists() or (candidate / "setup.py").exists():
            return candidate
        return Path.cwd()

    def model_dump_json(self, **kwargs: Any) -> str:
        return super().model_dump_json(**kwargs)


def load_settings() -> Settings:
    return Settings()


def save_settings(settings: Settings) -> None:
    settings.config_dir.mkdir(parents=True, exist_ok=True)
    settings.config_file.write_text(settings.model_dump_json(indent=2))
