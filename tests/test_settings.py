import json

import pytest
from jarvis.config.settings import Settings, LLMSettings


def test_settings_defaults():
    settings = Settings()
    assert settings.llm.provider == "auto"
    assert settings.llm.model == "llama3.1:8b"
    assert settings.voice.enabled is True
    assert settings.memory.enabled is True


def test_llm_settings():
    llm = LLMSettings(provider="openai", model="gpt-4")
    assert llm.provider == "openai"
    assert llm.model == "gpt-4"


def test_settings_serialization():
    settings = Settings()
    json_str = settings.model_dump_json()
    assert "auto" in json_str
    assert "llama3.1:8b" in json_str


def test_settings_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("os.path.expanduser", lambda path: str(tmp_path) if path.startswith("~") else path)
    settings = Settings()
    settings.llm.model = "round-trip-model"
    settings.skills.enabled = ["code_assistant"]

    from jarvis.config.settings import save_settings, load_settings
    save_settings(settings)

    loaded = load_settings()
    assert loaded.llm.model == "round-trip-model"
    assert loaded.skills.enabled == ["code_assistant"]


def test_invalid_settings_file_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr("os.path.expanduser", lambda path: str(tmp_path) if path.startswith("~") else path)
    config_dir = tmp_path / ".jarvis"
    config_dir.mkdir()
    (config_dir / "config.json").write_text("{invalid", encoding="utf-8")

    from jarvis.config.settings import load_settings
    with pytest.raises(RuntimeError, match="Failed to load configuration"):
        load_settings()