"""The top-level parser's help text must not trip the wrong-profile fallback warning.

``main._apply_profile_override`` builds the parser (``top_level_value_flag_sets``) before it
re-homes the process to the sticky ``active_profile``; a help string that resolved the home through
``get_jarvis_home()`` printed ``[JARVIS_HOME fallback] ... wrong profile`` on every ``jarvis``
command for users of ``jarvis profile use`` (#112319, also reported in #112839).
"""

from pathlib import Path

import pytest


@pytest.fixture
def sticky_profile_home(monkeypatch, tmp_path):
    import jarvis_constants

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("JARVIS_HOME", raising=False)
    root = tmp_path / ".jarvis"
    (root / "profiles" / "coder").mkdir(parents=True)
    (root / "active_profile").write_text("coder\n", encoding="utf-8")
    monkeypatch.setattr(jarvis_constants, "_profile_fallback_warned", False)
    return root


def test_building_the_parser_before_the_profile_override_stays_silent(sticky_profile_home, capsys):
    from jarvis_cli._parser import build_top_level_parser

    build_top_level_parser()

    assert "JARVIS_HOME fallback" not in capsys.readouterr().err


def test_help_text_names_the_profile_config_once_the_process_is_re_homed(sticky_profile_home, monkeypatch):
    from jarvis_cli._parser import _cfg_path

    monkeypatch.setenv("JARVIS_HOME", str(sticky_profile_home / "profiles" / "coder"))

    assert _cfg_path() == "~/.jarvis/profiles/coder/config.yaml"
