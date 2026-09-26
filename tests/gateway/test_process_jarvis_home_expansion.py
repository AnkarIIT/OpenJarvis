"""Gateway identity-file readers expand a literal ``~`` in JARVIS_HOME.

``python -m gateway.run`` never passes through the CLI's ``normalize_jarvis_home_env()``, so the
process-level home readers (PID/lock/status, lifecycle ledger, heartbeat) must expand on their own
or a fish-style ``JARVIS_HOME='~/.jarvis'`` lands the identity files under ``<cwd>/~/.jarvis``.
"""

from pathlib import Path

import pytest

from gateway import lifecycle_ledger, shutdown_watchdog, status


@pytest.mark.parametrize(
    "reader",
    [status._get_process_jarvis_home, lifecycle_ledger._process_jarvis_home,
     shutdown_watchdog._process_jarvis_home],
    ids=["status", "lifecycle_ledger", "shutdown_watchdog"],
)
def test_process_home_readers_expand_literal_tilde(reader, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("JARVIS_HOME", "~/.x")
    assert reader() == tmp_path / ".x"
    assert reader().is_absolute()
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / ".abs"))
    assert reader() == Path(tmp_path / ".abs")
