"""Instance-scoping of the uninspectable-holder fallback.

Field-verified 2026-09-07 on a production host running TWO independent
Jarvis instances: a main gateway (user ``ubuntu``,
JARVIS_HOME=/home/ubuntu/.jarvis) and a demo gateway (user ``demo``,
JARVIS_HOME=/home/demo/.jarvis).  The demo gateway runs as another user, so
its ``/proc/<pid>/fd`` table is unreadable from the main instance and the
holder scan falls back to ``/proc/<pid>/cmdline`` + ``_looks_like_jarvis``.
The demo process's argv matches the Jarvis patterns exactly, so the fallback
flagged it as an uninspectable holder of the MAIN instance's state.db even
though ``lsof`` proved zero open handles on it.  Consequence: the stale-FTS
rebuild in ``jarvis_state_schema._recover_stale_fts`` was deferred 42 times
across 6 gateway restarts, the ``fts_stale`` breadcrumb never cleared, and
FTS self-repair stayed permanently disabled.

PR #92419 fixed substring false positives (journalctl/grep mentioning
jarvis); a genuine second instance with a DIFFERENT JARVIS_HOME is still
misjudged on current main (issue #92401).

Behavior contract: an uninspectable holder identified only by argv must be
counted unless its own argv proves it is scoped to a *different* Jarvis
home / state.db and never references ours.  Ambiguous argv (no absolute
paths at all) must remain fail-closed, exactly as before — the conservative
intent of the fallback is preserved.
"""

import os

import pytest

import jarvis_state_holders

# Capture the pristine stdlib functions at import time: monkeypatched calls
# re-enter these closures, and re-capturing ``os.listdir`` after a previous
# patch would compose the fakes into a double path-rewrite.
_REAL_LISTDIR = os.listdir
_REAL_READLINK = os.readlink


# Representative demo-gateway argv on the two-instance host: every absolute
# token lives under /home/demo/.jarvis, the binary name matches the Jarvis
# patterns, and nothing references the main instance's home or state.db.
DEMO_HOME_ARGV = [
    "/home/demo/.jarvis/jarvis-agent/jarvis",
    "gateway",
    "run",
]

# Same, spelled through the venv interpreter + jarvis launcher script.
DEMO_VENV_ARGV = [
    "/home/demo/.jarvis/jarvis-agent/venv/bin/python",
    "/home/demo/.jarvis/jarvis-agent/jarvis_cli/main.py",
    "gateway",
]

# A Jarvis-shaped argv with no absolute paths: cannot disprove that this
# process touches our state.db, so it must stay fail-closed.
AMBIGUOUS_ARGV = ["jarvis", "gateway", "run"]


def _install_fake_proc(monkeypatch, tmp_path, unreadable_pids=(), fd_pids=()):
    """Redirect the module's /proc access to an inert fake tree.

    PIDs in ``unreadable_pids`` raise PermissionError on their fd dir
    (cross-user process); PIDs in ``fd_pids`` expose an empty-but-listable
    fd dir whose single descriptor fails readlink with EACCES
    (uninspectable-descriptor branch).
    """
    proc_root = tmp_path / "proc"
    for pid in set(unreadable_pids) | set(fd_pids):
        (proc_root / str(pid)).mkdir(parents=True, exist_ok=True)
    for pid in fd_pids:
        (proc_root / str(pid) / "fd").mkdir(exist_ok=True)
        (proc_root / str(pid) / "fd" / "3").touch(exist_ok=True)

    monkeypatch.setattr(jarvis_state_holders.os, "getpid", lambda: 111)

    def _listdir(path):
        if isinstance(path, str):
            for pid in unreadable_pids:
                if path == f"/proc/{pid}/fd":
                    raise PermissionError(errno_value("EACCES"), path)
            path = path.replace("/proc", str(proc_root))
        return _REAL_LISTDIR(path)

    monkeypatch.setattr(jarvis_state_holders.os, "listdir", _listdir)

    def _readlink(path):
        if "222/fd/3" in str(path):
            raise PermissionError(errno_value("EACCES"), str(path))
        return _REAL_READLINK(str(path).replace("/proc", str(proc_root)))

    monkeypatch.setattr(jarvis_state_holders.os, "readlink", _readlink)


def errno_value(name):
    import errno

    return getattr(errno, name)


def _install_fake_argv(monkeypatch, argv_by_pid):
    monkeypatch.setattr(
        jarvis_state_holders,
        "_read_proc_argv",
        lambda pid: list(argv_by_pid.get(pid)) if pid in argv_by_pid else None,
    )


@pytest.mark.linux_only
class TestUninspectableHolderInstanceScope:
    def test_other_instance_argv_is_not_a_holder_of_our_db(self, tmp_path, monkeypatch):
        """RED: fd dir unreadable + argv proves the process belongs to a
        DIFFERENT Jarvis home → not a holder of our state.db."""
        db_path = tmp_path / "state.db"
        _install_fake_proc(monkeypatch, tmp_path, unreadable_pids=(222,))
        _install_fake_argv(monkeypatch, {222: DEMO_HOME_ARGV})

        holders = jarvis_state_holders.foreign_state_db_holders(db_path)
        assert holders == []

    def test_argv_referencing_our_db_stays_flagged(self, tmp_path, monkeypatch):
        """A (possibly second) instance whose argv names OUR state.db, our
        sidecars, or our home must still be fail-closed flagged."""
        db_path = tmp_path / "state.db"
        our_home = str(tmp_path)

        for argv in (
            ["jarvis", f"--db={db_path}", "gateway"],
            ["jarvis", "checkpoint", f"{db_path}-wal"],
            ["jarvis", "--home", our_home, "gateway"],
        ):
            assert jarvis_state_holders._looks_like_jarvis(argv) or argv[0] == "jarvis"
            _install_fake_proc(monkeypatch, tmp_path, unreadable_pids=(222,))
            _install_fake_argv(monkeypatch, {222: argv})

            holders = jarvis_state_holders.foreign_state_db_holders(db_path)
            assert [pid for pid, _ in holders] == [222], argv
            assert holders[0][1].startswith("uninspectable holder:"), argv
