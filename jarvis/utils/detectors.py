from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from typing import Any


def check_python_version(min_version: tuple[int, int] = (3, 10)) -> bool:
    return sys.version_info >= min_version


def check_ollama() -> dict[str, Any]:
    result = {"available": False, "version": None, "models": []}

    ollama_path = shutil.which("ollama")
    if not ollama_path:
        return result

    try:
        version_output = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if version_output.returncode == 0:
            result["available"] = True
            result["version"] = version_output.stdout.strip()

        list_output = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if list_output.returncode == 0:
            lines = list_output.stdout.strip().split("\n")[1:]
            result["models"] = [line.split()[0] for line in lines if line.strip()]
    except Exception:
        pass

    return result


def check_llama_cpp() -> dict[str, Any]:
    result = {"available": False, "version": None}

    llama_server = shutil.which("llama-server")
    if llama_server:
        try:
            version_output = subprocess.run(
                [llama_server, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if version_output.returncode == 0:
                result["available"] = True
                result["version"] = version_output.stdout.strip()
        except Exception:
            pass

    return result


def check_lm_studio() -> dict[str, Any]:
    result = {"available": False}

    system = platform.system().lower()
    if system == "darwin":
        app_path = Path("/Applications/LM Studio.app")
    elif system == "windows":
        app_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "LM Studio" / "LM Studio.exe"
    else:
        app_path = Path.home() / ".local" / "share" / "lm-studio" / "LM Studio"

    if app_path.exists():
        result["available"] = True

    return result


def check_gpt4all() -> dict[str, Any]:
    result = {"available": False}

    gpt4all_path = shutil.which("gpt4all")
    if gpt4all_path:
        result["available"] = True

    return result


def detect_all_local_ai() -> dict[str, dict[str, Any]]:
    return {
        "ollama": check_ollama(),
        "llama_cpp": check_llama_cpp(),
        "lm_studio": check_lm_studio(),
        "gpt4all": check_gpt4all(),
    }


def get_system_info() -> dict[str, Any]:
    import psutil

    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": sys.version,
        "cpu_count": psutil.cpu_count(),
        "memory_total": psutil.virtual_memory().total,
        "memory_available": psutil.virtual_memory().available,
        "disk_usage": psutil.disk_usage("/").free if platform.system() != "Windows" else psutil.disk_usage("C:").free,
    }


from pathlib import Path
import os