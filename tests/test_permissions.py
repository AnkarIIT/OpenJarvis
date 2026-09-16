from jarvis.agent.permissions import action_policy, confirmation_required_result, requires_confirmation
from jarvis.config.settings import Settings


def test_dangerous_mcp_actions_require_confirmation_by_default():
    settings = Settings()
    assert requires_confirmation(settings, "terminal") is True
    assert requires_confirmation(settings, "memory") is False
    assert action_policy(settings, "git", "git_status") == "allow"


def test_confirmation_can_be_disabled_explicitly():
    settings = Settings()
    settings.mcp.require_confirmation = False
    assert requires_confirmation(settings, "terminal") is False


def test_explicit_tool_policy_overrides_server_default():
    settings = Settings()
    settings.mcp.tool_policies = {
        "git:git_status": "allow",
        "git:git_commit": "confirm",
        "terminal:run_command": "deny",
    }
    assert action_policy(settings, "git", "git_status") == "allow"
    assert action_policy(settings, "git", "git_commit") == "confirm"
    assert action_policy(settings, "terminal", "run_command") == "deny"


def test_confirmation_result_is_explicit():
    result = confirmation_required_result("run_command", "terminal")
    assert result["error"] == "confirmation_required"
    assert "not executed" in result["message"]
