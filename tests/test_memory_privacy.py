import pytest

from jarvis.config.settings import Settings
from jarvis.memory.privacy import contains_sensitive_data


def test_secret_detection():
    assert contains_sensitive_data("api_key=abc123")
    assert contains_sensitive_data("Authorization: Bearer abc.def")
    assert not contains_sensitive_data("User prefers dark mode")


@pytest.mark.asyncio
async def test_memory_policy_defaults():
    settings = Settings()
    assert settings.memory.allow_sensitive is False
    assert settings.memory.retention_days == 0
