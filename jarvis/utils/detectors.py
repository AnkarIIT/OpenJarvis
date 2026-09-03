from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
import os


def check_python_version(min_version: tuple[int, int] = (3, 10)) -> bool:
    return sys.version_info >= min_version


def check_ollama() -> dict[str, Any]:
    result = {"available": False, "version": None, "models": [], "running": False}

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

        ps_output = subprocess.run(
            ["ollama", "ps"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        result["running"] = ps_output.returncode == 0 and ps_output.stdout.strip()
    except Exception:
        pass

    return result


def check_llama_cpp() -> dict[str, Any]:
    result = {"available": False, "version": None, "models": []}

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

    common_model_dirs = [
        Path.home() / ".cache" / "llama.cpp",
        Path.home() / "models",
        Path("/usr/local/share/llama.cpp/models"),
    ]
    for d in common_model_dirs:
        if d.exists():
            result["models"].extend([f.name for f in d.glob("*.gguf")])

    return result


def check_lm_studio() -> dict[str, Any]:
    result = {"available": False, "models": []}

    system = platform.system().lower()
    if system == "darwin":
        app_path = Path("/Applications/LM Studio.app")
    elif system == "windows":
        app_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "LM Studio" / "LM Studio.exe"
    else:
        app_path = Path.home() / ".local" / "share" / "lm-studio" / "LM Studio"

    if app_path.exists():
        result["available"] = True

    lmstudio_models = Path.home() / ".cache" / "lm-studio" / "models"
    if lmstudio_models.exists():
        result["models"] = [f.name for f in lmstudio_models.rglob("*.gguf")]

    return result


def check_gpt4all() -> dict[str, Any]:
    result = {"available": False, "models": []}

    gpt4all_path = shutil.which("gpt4all")
    if gpt4all_path:
        result["available"] = True

    gpt4all_models = Path.home() / ".cache" / "gpt4all"
    if gpt4all_models.exists():
        result["models"] = [f.name for f in gpt4all_models.glob("*.gguf")]

    return result


def check_vllm() -> dict[str, Any]:
    result = {"available": False, "version": None}
    try:
        import vllm
        result["available"] = True
        result["version"] = vllm.__version__
    except ImportError:
        pass
    return result


def detect_all_local_ai() -> dict[str, dict[str, Any]]:
    return {
        "ollama": check_ollama(),
        "llama_cpp": check_llama_cpp(),
        "lm_studio": check_lm_studio(),
        "gpt4all": check_gpt4all(),
        "vllm": check_vllm(),
    }


def get_available_models() -> list[dict[str, Any]]:
    models = []
    all_ai = detect_all_local_ai()

    for provider, info in all_ai.items():
        if info["available"]:
            if info["models"]:
                for model in info["models"]:
                    models.append({
                        "provider": provider,
                        "model": model,
                        "display": f"{provider}: {model}",
                        "source": "local",
                    })
            else:
                models.append({
                    "provider": provider,
                    "model": None,
                    "display": f"{provider} (installed, no models)",
                    "source": "local",
                })

    recommended = [
        {"provider": "ollama", "model": "llama3.1:8b", "display": "Ollama: Llama 3.1 8B (4.7GB) - Recommended", "source": "download", "ram_gb": 8},
        {"provider": "ollama", "model": "qwen2.5:7b", "display": "Ollama: Qwen 2.5 7B (4.4GB)", "source": "download", "ram_gb": 8},
        {"provider": "ollama", "model": "deepseek-coder:6.7b", "display": "Ollama: DeepSeek Coder 6.7B (3.8GB)", "source": "download", "ram_gb": 6},
        {"provider": "ollama", "model": "phi3:mini", "display": "Ollama: Phi-3 Mini (2.3GB) - Low RAM", "source": "download", "ram_gb": 4},
        {"provider": "ollama", "model": "gemma2:9b", "display": "Ollama: Gemma 2 9B (5.4GB)", "source": "download", "ram_gb": 10},
    ]
    for r in recommended:
        r["recommended"] = True

    return models + recommended


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


def format_bytes(bytes_val: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f}PB"