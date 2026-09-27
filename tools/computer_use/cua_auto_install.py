"""cua-driver auto-install: best-effort one-shot install when the tool is first used.

Mirrors ``tools/browser_tool_install._try_auto_install_chromium``: gated by
``security.allow_lazy_installs``, skipped in Docker, attempted once per process.
"""


from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from jarvis_cli._subprocess_compat import windows_hide_flags
from jarvis_cli.config import load_config
from jarvis_cli.tools_config_cua import (
    _CUA_INSTALL_PS1_URL,
    _CUA_INSTALL_SH_URL,
    _CUA_MANUAL_README,
    _cua_driver_cmd,
    _cua_install_home,
    _cua_install_lock_dir,
    _cua_windows_install_lock_file,
    _clear_stale_windows_cua_install_lock,
    _resolved_cua_driver_cmd,
    _run_cua_driver_installer,
    _cua_install_target_writable,
)
from tools.computer_use.cua_backend_driver import cua_driver_binary_available as _binary_available

logger = logging.getLogger(__name__)

# One attempt per process — same contract as browser's _chromium_autoinstall_attempted.
_CUA_AUTINSTALL_ATTEMPTED = False


def _allow_lazy_installs() -> bool:
    """Mirror browser's gate: ``security.allow_lazy_installs`` (default True)."""
    try:
        cfg = load_config() or {}
        return bool(cfg.get("security", {}).get("allow_lazy_installs", True))
    except Exception:
        return True


def _running_in_docker() -> bool:
    """Best-effort Docker detection (same as browser)."""
    if os.path.exists("/.dockerenv"):
        return True
    try:
        with open("/proc/1/cgroup", "rt", encoding="utf-8") as fp:
            return "docker" in fp.read()
    except OSError:
        return False


def try_auto_install_cua_driver() -> bool:
    """Best-effort one-shot cua-driver install. Returns True if the driver is now available.

    Called from ``handle_computer_use`` when the backend is unavailable, and from
    ``check_computer_use_requirements`` so the tool's ``check_fn`` can advertise it
    after a successful auto-install.
    """
    global _CUA_AUTINSTALL_ATTEMPTED
    if _binary_available():
        return True
    if _CUA_AUTINSTALL_ATTEMPTED:
        return False
    _CUA_AUTINSTALL_ATTEMPTED = True
    if _running_in_docker():
        logger.debug("computer_use: skipping auto-install in Docker")
        return False
    if not _allow_lazy_installs():
        logger.debug("computer_use: auto-install skipped — security.allow_lazy_installs is disabled")
        return False

    system = sys.platform
    if system not in ("darwin", "win32", "linux"):
        logger.debug("computer_use: unsupported platform %s for auto-install", system)
        return False

    is_windows = system == "win32"

    # Clear any stale Windows install lock from a previous crashed installer.
    if is_windows:
        try:
            _clear_stale_windows_cua_install_lock()
        except Exception as e:
            logger.debug("computer_use: failed to clear stale install lock: %s", e)

    fetch_tool = "powershell" if is_windows else "curl"
    if not shutil.which(fetch_tool):
        logger.warning(
            "computer_use: %s not found — cannot auto-install cua-driver. "
            "Install manually: %s",
            fetch_tool,
            _CUA_MANUAL_README,
        )
        return False

    if not _cua_install_target_writable():
        logger.warning(
            "computer_use: install target not writable — skipping auto-install. "
            "Run from an admin account or install cua-driver manually: %s",
            _CUA_MANUAL_README,
        )
        return False

    logger.info(
        "computer_use: cua-driver missing — auto-installing (one-time, gated by security.allow_lazy_installs). "
        "Disable via config.yaml: security.allow_lazy_installs: false"
    )
    ok = _run_cua_driver_installer(
        label="Installing",
        verbose=False,
        installer_timeout=600,
    )
    if ok:
        logger.info("computer_use: cua-driver auto-install succeeded")
    else:
        logger.warning(
            "computer_use: cua-driver auto-install failed. "
            "Install manually: %s",
            _CUA_MANUAL_README,
        )
    return _binary_available()
