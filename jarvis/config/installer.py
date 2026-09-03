from __future__ import annotations

import asyncio
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.prompt import Confirm, Prompt

from jarvis.config.settings import Settings, load_settings, save_settings
from jarvis.utils.detectors import check_ollama, check_python_version
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)
console = Console()


class Installer:
    DEFAULT_MODEL = "llama3.1:8b"
    VOICE_MODELS = {
        "piper": {
            "en_US-lessac-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        },
        "vosk": {
            "vosk-model-en-us-0.22": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip",
        },
    }

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.config_dir = self.settings.config_dir
        self.ollama_installed = False

    async def run(self) -> bool:
        console.print("\n[bold cyan]🤖 JARVIS Terminal Agent - Automated Setup[/bold cyan]\n")

        if not await self._check_prerequisites():
            return False

        if not await self._detect_and_install_ai():
            return False

        await self._download_voice_models()
        await self._setup_mcp_servers()
        self._create_config()
        self._add_to_path()

        console.print("\n[bold green]✅ JARVIS setup complete![/bold green]")
        console.print("Run [bold]jarvis[/bold] to start.\n")
        return True

    async def _check_prerequisites(self) -> bool:
        console.print("[cyan]Checking prerequisites...[/cyan]")

        if not check_python_version():
            console.print("[red]❌ Python 3.10+ required[/red]")
            return False

        console.print("[green]✓ Python version OK[/green]")
        return True

    async def _detect_and_install_ai(self) -> bool:
        console.print("\n[cyan]Detecting local AI...[/cyan]")

        ollama_status = check_ollama()

        if ollama_status["available"]:
            console.print(f"[green]✓ Ollama found: {ollama_status['version']}[/green]")
            self.ollama_installed = True
        else:
            console.print("[yellow]⚠ Ollama not found[/yellow]")
            if Confirm.ask("Install Ollama automatically?", default=True):
                if await self._install_ollama():
                    console.print("[green]✓ Ollama installed[/green]")
                    self.ollama_installed = True
                else:
                    console.print("[red]❌ Failed to install Ollama[/red]")
                    return False
            else:
                console.print("[yellow]Skipping Ollama installation[/yellow]")
                return False

        if self.ollama_installed:
            await self._pull_model()

        return True

    async def _install_ollama(self) -> bool:
        system = platform.system().lower()

        try:
            if system == "windows":
                return await self._install_ollama_windows()
            elif system == "darwin":
                return await self._install_ollama_macos()
            else:
                return await self._install_ollama_linux()
        except Exception as e:
            logger.error(f"Ollama installation failed: {e}")
            return False

    async def _install_ollama_windows(self) -> bool:
        url = "https://ollama.com/download/OllamaSetup.exe"
        installer_path = Path.home() / "Downloads" / "OllamaSetup.exe"

        console.print("Downloading Ollama installer...")
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("Downloading...", total=None)
            urllib.request.urlretrieve(
                url, installer_path,
                reporthook=lambda *args: self._download_hook(progress, task, *args)
            )

        console.print("Running Ollama installer (requires admin)...")
        result = subprocess.run([str(installer_path), "/S"], capture_output=True)
        return result.returncode == 0

    async def _install_ollama_macos(self) -> bool:
        result = subprocess.run(["brew", "install", "ollama"], capture_output=True)
        return result.returncode == 0

    async def _install_ollama_linux(self) -> bool:
        result = subprocess.run(
            ["curl", "-fsSL", "https://ollama.com/install.sh", "|", "sh"],
            shell=True, capture_output=True
        )
        return result.returncode == 0

    def _download_hook(self, progress: Progress, task: TaskID, block_num: int, block_size: int, total_size: int):
        if total_size > 0:
            progress.update(task, total=total_size, completed=block_num * block_size)

    async def _pull_model(self) -> None:
        console.print(f"\n[cyan]Pulling model: {self.DEFAULT_MODEL}[/cyan]")

        process = await asyncio.create_subprocess_exec(
            "ollama", "pull", self.DEFAULT_MODEL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        async for line in process.stdout:
            line = line.decode().strip()
            if line:
                console.print(f"  {line}")

        await process.wait()

        if process.returncode == 0:
            console.print(f"[green]✓ Model {self.DEFAULT_MODEL} ready[/green]")
            self.settings.llm.model = self.DEFAULT_MODEL
        else:
            console.print(f"[red]❌ Failed to pull model[/red]")

    async def _download_voice_models(self) -> None:
        if not self.settings.voice.enabled:
            return

        console.print("\n[cyan]Downloading voice models...[/cyan]")
        voice_dir = self.config_dir / "voice"
        voice_dir.mkdir(parents=True, exist_ok=True)

        for engine, models in self.VOICE_MODELS.items():
            for model_name, url in models.items():
                model_path = voice_dir / model_name
                if model_path.exists():
                    console.print(f"[green]✓ {model_name} already exists[/green]")
                    continue

                console.print(f"Downloading {model_name}...")
                try:
                    urllib.request.urlretrieve(url, voice_dir / f"{model_name}.tmp")
                    (voice_dir / f"{model_name}.tmp").rename(model_path)
                    console.print(f"[green]✓ {model_name} downloaded[/green]")
                except Exception as e:
                    logger.error(f"Failed to download {model_name}: {e}")
                    console.print(f"[yellow]⚠ Failed to download {model_name}[/yellow]")

    async def _setup_mcp_servers(self) -> None:
        console.print("\n[cyan]Setting up MCP servers...[/cyan]")

        default_servers = {
            "filesystem": {
                "command": "jarvis-mcp-filesystem",
                "args": ["--root", str(Path.home())],
            },
            "terminal": {
                "command": "jarvis-mcp-terminal",
                "args": ["--allow", "ls,cat,grep,git,python,pip,npm"],
            },
            "git": {
                "command": "jarvis-mcp-git",
            },
            "memory": {
                "command": "jarvis-mcp-memory",
                "args": ["--path", str(self.settings.memory_path)],
            },
        }

        self.settings.mcp.servers = default_servers
        console.print("[green]✓ MCP servers configured[/green]")

    def _create_config(self) -> None:
        console.print("\n[cyan]Creating configuration...[/cyan]")
        save_settings(self.settings)
        console.print(f"[green]✓ Config saved to {self.settings.config_file}[/green]")

    def _add_to_path(self) -> None:
        console.print("\n[cyan]Adding to PATH...[/cyan]")

        if platform.system() == "Windows":
            user_path = os.environ.get("PATH", "")
            jarvis_path = str(Path(sys.executable).parent / "Scripts")
            if jarvis_path not in user_path:
                console.print(f"[yellow]Add to PATH manually: {jarvis_path}[/yellow]")
        else:
            shell_rc = Path.home() / ".bashrc"
            if not shell_rc.exists():
                shell_rc = Path.home() / ".zshrc"

            jarvis_bin = Path.home() / ".local" / "bin"
            export_line = f'export PATH="{jarvis_bin}:$PATH"'

            if shell_rc.exists():
                content = shell_rc.read_text()
                if export_line not in content:
                    with open(shell_rc, "a") as f:
                        f.write(f"\n{export_line}\n")
                    console.print(f"[green]✓ Added to {shell_rc}[/green]")
            else:
                console.print(f"[yellow]Add to PATH manually: {jarvis_bin}[/yellow]")


async def install() -> bool:
    installer = Installer()
    return await installer.run()


if __name__ == "__main__":
    asyncio.run(install())