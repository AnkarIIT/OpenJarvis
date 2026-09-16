from jarvis.agent.permissions import confirmation_required_result, requires_confirmation
from jarvis.config.settings import Settings


def test_dangerous_mcp_actions_require_confirmation_by_default():
    settings = Settings()
    assert requires_confirmation(settings, "terminal") is True
    assert requires_confirmation(settings, "memory") is False


def test_confirmation_can_be_disabled_explicitly():
    settings = Settings()
    settings.mcp.require_confirmation = False
    assert requires_confirmation(settings, "terminal") is False


def test_confirmation_result_is_explicit():
    result = confirmation_required_result("run_command", "terminal")
    assert result["error"] == "confirmation_required"
    assert "not executed" in result["message"]
