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