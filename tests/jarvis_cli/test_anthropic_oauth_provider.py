"""Invariant tests for Anthropic OAuth provider flow registration.

Verifies that Anthropic is registered in OAUTH_PROVIDER_FLOWS with correct
resolve/status functions, terminal refresh codes, and logout behavior — so
that ``jarvis doctor``, auto provider resolution, and ``jarvis logout`` all
recognize an Anthropic OAuth login (previously Anthropic fell through to the
API-key status path, hiding pool credentials from status checks).
"""

from __future__ import annotations

import json

import pytest

from jarvis_cli.auth import (
    AuthError,
    OAUTH_PROVIDER_FLOWS,
    _BESPOKE_STATUS_FUNCTIONS,
    _is_terminal_anthropic_oauth_refresh_error,
    _is_terminal_refresh_error,
    _logout_default_provider_from_config,
    get_anthropic_auth_status,
    get_auth_status,
    resolve_anthropic_runtime_credentials,
)


# ── Registration invariants ──────────────────────────────────────────────────


def test_anthropic_registered_in_oauth_provider_flows():
    """Anthropic must be in OAUTH_PROVIDER_FLOWS so get_auth_status(),
    _logged_in_oauth_active_provider(), and logout all see OAuth tokens."""
    flow = OAUTH_PROVIDER_FLOWS["anthropic"]
    assert flow.provider_id == "anthropic"
    assert flow.resolve_fn == "resolve_anthropic_runtime_credentials"
    assert flow.status_fn == "get_anthropic_auth_status"
    assert flow.logout_from_config is True
    # Terminal codes must include the standard dead-grant codes plus anthropic-specific
    assert "invalid_grant" in flow.terminal_refresh_codes
    assert "invalid_token" in flow.terminal_refresh_codes
    assert "refresh_token_reused" in flow.terminal_refresh_codes
    assert "anthropic_refresh_failed" in flow.terminal_refresh_codes


def test_anthropic_in_bespoke_status_dispatch():
    """get_auth_status('anthropic') must dispatch to get_anthropic_auth_status,
    NOT fall through to get_api_key_provider_status (which only checks env)."""
    assert _BESPOKE_STATUS_FUNCTIONS["anthropic"] == "get_anthropic_auth_status"


# ── Status function behavior ────────────────────────────────────────────────


def test_get_anthropic_auth_status_not_logged_in_without_credentials(tmp_path, monkeypatch):
    """With no credentials anywhere, status must report logged_in=False."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / "jarvis"))
    status = get_anthropic_auth_status()
    assert status["logged_in"] is False


def test_get_auth_status_anthropic_uses_oauth_not_api_key(tmp_path, monkeypatch):
    """The generic dispatcher must route to the OAuth status builder, not the
    api_key fallback that only scans env vars."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / "jarvis"))
    # get_auth_status dispatches to get_anthropic_auth_status (bespoke)
    status = get_auth_status("anthropic")
    assert status["logged_in"] is False
    assert "auth_store" in status


def test_get_anthropic_auth_status_detects_api_key_in_env(tmp_path, monkeypatch):
    """An ANTHROPIC_API_KEY env var must show as logged-in with api_key mode."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / "jarvis"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api0123456789")
    status = get_anthropic_auth_status()
    assert status["logged_in"] is True
    assert status["auth_mode"] == "api_key"
    assert status["source"] == "env"
    assert status["api_key"] == "sk-ant-api0123456789"


def test_get_anthropic_auth_status_detects_oauth_token_in_env(tmp_path, monkeypatch):
    """A CLAUDE_CODE_OAUTH_TOKEN env var must show as logged-in with oauth mode."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / "jarvis"))
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat-test-token")
    status = get_anthropic_auth_status()
    assert status["logged_in"] is True
    assert status["auth_mode"] == "oauth"
    assert status["source"] == "env"


# ── Resolve function behavior ───────────────────────────────────────────────


def test_resolve_anthropic_runtime_credentials_no_creds_raises(tmp_path, monkeypatch):
    """No credentials anywhere → AuthError with code 'no_credentials'."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / "jarvis"))
    with pytest.raises(AuthError) as exc_info:
        resolve_anthropic_runtime_credentials()
    assert exc_info.value.code == "no_credentials"


def test_resolve_anthropic_runtime_credentials_env_api_key(tmp_path, monkeypatch):
    """Env var API key must be returned by resolve."""
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / "jarvis"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api0123456789")
    result = resolve_anthropic_runtime_credentials()
    assert result["provider"] == "anthropic"
    assert result["api_key"] == "sk-ant-api0123456789"
    assert result["auth_mode"] == "api_key"
    # Pool seeds env vars, so source is pool:<env_var>, not "env"
    assert "pool" in result["source"] or result["source"] == "env"
    assert result["base_url"] == "https://api.anthropic.com"


# ── Terminal refresh error ──────────────────────────────────────────────────


def test_is_terminal_anthropic_oauth_refresh_error_dead_grant():
    """invalid_grant must be terminal for anthropic (retrying the same refresh token cannot succeed)."""
    exc = AuthError("dead grant", provider="anthropic", code="invalid_grant", relogin_required=True)  # type: ignore[call-arg]
    assert _is_terminal_anthropic_oauth_refresh_error(exc) is True


def test_is_terminal_anthropic_refresh_error_does_not_flag_other_providers():
    """A Nous invalid_grant must NOT be flagged as terminal for anthropic."""
    exc = AuthError("dead grant", provider="nous", code="invalid_grant", relogin_required=True)  # type: ignore[call-arg]
    assert _is_terminal_anthropic_oauth_refresh_error(exc) is False


def test_is_terminal_anthropic_refresh_error_non_terminal_code():
    """A non-terminal code (e.g. 'timeout') must not be flagged."""
    exc = AuthError("timeout", provider="anthropic", code="timeout", relogin_required=False)  # type: ignore[call-arg]
    assert _is_terminal_anthropic_oauth_refresh_error(exc) is False


# ── Logout behavior ─────────────────────────────────────────────────────────


def test_logout_resets_config_provider_for_anthropic(tmp_path, monkeypatch):
    """Logout must reset config.yaml model.provider when it is anthropic."""
    import yaml
    jarvis_home = tmp_path / "jarvis"
    jarvis_home.mkdir(parents=True)
    (jarvis_home / "config.yaml").write_text(yaml.dump({
        "model": {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022"},
    }))
    monkeypatch.setenv("JARVIS_HOME", str(jarvis_home))
    assert _logout_default_provider_from_config() == "anthropic"


def test_logout_does_not_reset_config_provider_for_other(tmp_path, monkeypatch):
    """Logout must NOT reset config.yaml model.provider when it is openai-api."""
    import yaml
    jarvis_home = tmp_path / "jarvis"
    jarvis_home.mkdir(parents=True)
    (jarvis_home / "config.yaml").write_text(yaml.dump({
        "model": {"provider": "openai-api", "model": "gpt-4"},
    }))
    monkeypatch.setenv("JARVIS_HOME", str(jarvis_home))
    assert _logout_default_provider_from_config() is None
