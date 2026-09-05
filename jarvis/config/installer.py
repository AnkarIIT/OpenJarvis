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
from rich.table import Table

from jarvis.config.settings import Settings, load_settings, save_settings
from jarvis.utils.detectors import (
    check_python_version,
    detect_all_local_ai,
    get_available_models,
    get_system_info,
    format_bytes,
)
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)
console = Console()


class Installer:
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
        self.selected_provider = None
        self.selected_model = None

    async def run(self) -> bool:
        console.print("\n[bold cyan]JARVIS Terminal Agent - Setup[/bold cyan]\n")

        if not await self._check_prerequisites():
            return False

        if not await self._detect_and_select_ai():
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
            console.print("[red]ERROR: Python 3.10+ required[/red]")
            return False

        sys_info = get_system_info()
        ram_gb = sys_info["memory_total"] / (1024**3)
        console.print(f"[green]OK Python OK | RAM: {ram_gb:.1f}GB | CPU: {sys_info['cpu_count']} cores[/green]")

        if ram_gb < 4:
            console.print("[yellow]WARNING: Less than 4GB RAM - only small models will work[/yellow]")
        elif ram_gb < 8:
            console.print("[yellow]WARNING: 4-8GB RAM - recommend models under 4GB[/yellow]")

        return True

    async def _detect_and_select_ai(self) -> bool:
        console.print("\n[cyan]Detecting local AI installations...[/cyan]")

        all_ai = detect_all_local_ai()
        available_models = get_available_models()

        local_models = [m for m in available_models if m["source"] == "local"]
        downloadable = [m for m in available_models if m["source"] == "download"]

        self._display_detection_results(all_ai, local_models)

        if local_models:
            console.print("\n[green]Found existing local models:[/green]")
            return await self._select_from_existing(local_models)
        else:
            console.print("\n[yellow]No local models found.[/yellow]")
            return await self._recommend_and_install(downloadable)

    def _display_detection_results(self, all_ai: dict, local_models: list) -> None:
        table = Table(title="Local AI Detection Results")
        table.add_column("Provider", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Version", style="yellow")
        table.add_column("Models Found", style="white")

        for provider, info in all_ai.items():
            status = "[green]OK Available[/green]" if info["available"] else "[red]ERROR Not installed[/red]"
            version = info.get("version", "N/A")
            models = ", ".join(info.get("models", [])) if info.get("models") else "None"
            if len(models) > 50:
                models = models[:47] + "..."
            table.add_row(provider.replace("_", " ").title(), status, version, models)

        console.print(table)

    async def _select_from_existing(self, local_models: list) -> bool:
        console.print("\n[bold]Select a model to use:[/bold]")

        for i, model in enumerate(local_models, 1):
            console.print(f"  [{i}] {model['display']}")

        console.print(f"  [{len(local_models) + 1}] Install a different model instead")

        while True:
            choice = Prompt.ask("Enter choice", default="1")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(local_models):
                    self.selected_provider = local_models[idx]["provider"]
                    self.selected_model = local_models[idx]["model"]
                    break
                elif idx == len(local_models):
                    return await self._recommend_and_install(
                        [m for m in get_available_models() if m["source"] == "download"]
                    )
                else:
                    console.print("[red]Invalid choice[/red]")
            except ValueError:
                console.print("[red]Enter a number[/red]")

        console.print(f"\n[green]OK Using {self.selected_provider}: {self.selected_model}[/green]")
        self.settings.llm.provider = self.selected_provider
        self.settings.llm.model = self.selected_model
        return True

    async def _recommend_and_install(self, downloadable: list) -> bool:
        console.print("\n[bold]Recommended models to install:[/bold]")

        table = Table()
        table.add_column("#", style="cyan", width=3)
        table.add_column("Model", style="white")
        table.add_column("Size", style="yellow")
        table.add_column("RAM Needed", style="red")

        sys_info = get_system_info()
        ram_gb = sys_info["memory_total"] / (1024**3)

        for i, model in enumerate(downloadable, 1):
            if model.get("recommended"):
                size = model.get("size_gb", "?")
                size_str = f"{size}GB" if size != "?" else "Unknown"
                ram_needed = f"{model.get('ram_gb', '?')}GB"
                recommended = " [*]" if model.get("ram_gb", 99) <= ram_gb else " [!]"
                table.add_row(str(i), model["display"].split(" - ")[0] + recommended, size_str, ram_needed)

        console.print(table)
        console.print("[dim][*] = fits your RAM | [!] = may be slow[/dim]")

        console.print(f"\n  [{len(downloadable) + 1}] Install Ollama only (choose model later)")
        console.print(f"  [{len(downloadable) + 2}] Skip - configure manually later")

        while True:
            choice = Prompt.ask("Enter choice", default="1")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(downloadable):
                    self.selected_provider = downloadable[idx]["provider"]
                    self.selected_model = downloadable[idx]["model"]
                    break
                elif idx == len(downloadable):
                    self.selected_provider = "ollama"
                    self.selected_model = None
                    break
                elif idx == len(downloadable) + 1:
                    console.print("[yellow]Skipping AI setup[/yellow]")
                    return True
                else:
                    console.print("[red]Invalid choice[/red]")
            except ValueError:
                console.print("[red]Enter a number[/red]")

        if self.selected_provider == "ollama":
            return await self._install_ollama_and_model()
        elif self.selected_provider == "llama_cpp":
            return await self._download_gguf_model()
        elif self.selected_provider in ("lm_studio", "localai"):
            # These are managed externally via their GUI/desktop apps
            console.print(f"[yellow]{self.selected_provider} is managed via its desktop app. Configure the server URL in JARVIS settings.[/yellow]")
            self.settings.llm.provider = self.selected_provider
            self.settings.llm.base_url = "http://127.0.0.1:1234/v1" if self.selected_provider == "lm_studio" else "http://127.0.0.1:8080/v1"
            self.settings.llm.model = self.selected_model or "llama3.1"
            return True

        return True

    async def _install_ollama_and_model(self) -> bool:
        ollama_status = detect_all_local_ai()["ollama"]

        if not ollama_status["available"]:
            console.print("\n[cyan]Installing Ollama...[/cyan]")
            if not await self._install_ollama():
                console.print("[red]ERROR Failed to install Ollama[/red]")
                return False
            console.print("[green]OK Ollama installed[/green]")

        if self.selected_model:
            console.print(f"\n[cyan]Pulling model: {self.selected_model}[/cyan]")
            if not await self._pull_model(self.selected_model):
                return False

        self.settings.llm.provider = "ollama"
        self.settings.llm.model = self.selected_model or "llama3.1:8b"
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

    async def _pull_model(self, model: str) -> bool:
        process = await asyncio.create_subprocess_exec(
            "ollama", "pull", model,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        async for line in process.stdout:
            line = line.decode().strip()
            if line:
                console.print(f"  {line}")

        await process.wait()

        if process.returncode == 0:
            console.print(f"[green]OK Model {model} ready[/green]")
            return True
        else:
            console.print(f"[red]ERROR Failed to pull model[/red]")
            return False

    async def _download_gguf_model(self) -> bool:
        """Download a GGUF model directly (no Ollama needed)."""
        model_url = self.selected_model
        if not model_url or not model_url.startswith("http"):
            yield_skip = True
            return False

        model_dir = Path.home() / ".jarvis" / "models"
        model_dir.mkdir(parents=True, exist_ok=True)
        model_filename = model_url.split("/")[-1]
        model_path = model_dir / model_filename

        if model_path.exists():
            console.print(f"[green]OK {model_filename} already exists[/green]")
        else:
            console.print(f"\n[cyan]Downloading GGUF model: {model_filename}[/cyan]")
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
            ) as progress:
                task = progress.add_task("Downloading...", total=None)
                try:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: urllib.request.urlretrieve(
                            model_url, str(model_path),
                            reporthook=lambda *args: self._download_hook(progress, task, *args)
                        ),
                    )
                except Exception as e:
                    logger.error(f"Failed to download GGUF model: {e}")
                    console.print(f"[red]ERROR Download failed: {e}[/red]")
                    return False

            console.print(f"[green]OK Model downloaded to {model_path}[/green]")

        self.settings.llm.provider = "llama_cpp"
        self.settings.llm.model_path = str(model_path)
        self.settings.llm.model = model_filename
        return True

    async def _download_voice_models(self) -> None:
        if not self.settings.voice.enabled:
            return

        console.print("\n[cyan]Downloading voice models...[/cyan]")
        voice_dir = self.config_dir / "voice"
        voice_dir.mkdir(parents=True, exist_ok=True)

        for engine, models in self.VOICE_MODELS.items():
            for model_name, url in models.items():
                # Determine file path based on engine type
                if engine == "piper":
                    model_path = voice_dir / f"{model_name}.onnx"
                    if model_path.exists() or (voice_dir / f"{model_name}.onnx").exists():
                        console.print(f"[green]OK Piper {model_name} already exists[/green]")
                        continue
                    download_path = voice_dir / f"{model_name}.onnx.tmp"
                elif engine == "openwakeword":
                    model_path = voice_dir / f"{model_name}.tflite"
                    if model_path.exists():
                        continue
                    download_path = voice_dir / f"{model_name}.tflite.tmp"
                elif engine == "vosk":
                    model_path = voice_dir / model_name
                    if model_path.exists() or model_path.with_suffix(".zip").exists():
                        console.print(f"[green]OK Vosk {model_name} already exists[/green]")
                        continue
                    download_path = voice_dir / f"{model_name}.zip.tmp"
                elif engine == "whisper":
                    model_path = voice_dir / "whisper" / f"ggml-{model_name}.bin"
                    model_path.parent.mkdir(parents=True, exist_ok=True)
                    if model_path.exists():
                        console.print(f"[green]OK Whisper {model_name} already exists[/green]")
                        continue
                    download_path = model_path.with_suffix(".bin.tmp")
                elif engine == "porcupine":
                    # Skip - porcupine needs system-specific ppn files
                    continue
                else:
                    model_path = voice_dir / model_name
                    download_path = voice_dir / f"{model_name}.tmp"

                console.print(f"Downloading {model_name} ({engine})...")

                # Use async download with progress
                try:
                    loop = asyncio.get_event_loop()
                    await self._download_file(url, download_path, progress_desc=f"{model_name}")

                    download_path.rename(model_path)
                    console.print(f"[green]OK {model_name} downloaded[/green]")

                    # Handle zip extraction for Vosk
                    if engine == "vosk" and str(model_path).endswith(".zip"):
                        await self._extract_zip(model_path, voice_dir)
                except Exception as e:
                    logger.error(f"Failed to download {model_name}: {e}")
                    console.print(f"[yellow]WARNING: Failed to download {model_name}[/yellow]")

    async def _download_file(self, url: str, dest: Path, progress_desc: str = "") -> None:
        """Download a file with progress display."""
        import httpx

        async with httpx.AsyncClient(timeout=300) as http:
            async with http.stream("GET", url) as resp:
                if resp.status_code != 200:
                    raise Exception(f"HTTP {resp.status_code} from {url}")
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    DownloadColumn(),
                    TransferSpeedColumn(),
                    TimeRemainingColumn(),
                ) as progress:
                    task = progress.add_task(progress_desc or "Downloading...", total=None)
                    with open(dest, "wb") as f:
                        async for chunk in resp.aiter_bytes(8192):
                            f.write(chunk)
                            progress.advance(task, len(chunk))

    async def _extract_zip(self, zip_path: Path, dest_dir: Path) -> None:
        """Extract a zip file."""
        import zipfile
        console.print(f"  Extracting {zip_path.name}...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(dest_dir)
        # Optionally remove the zip
        console.print(f"  [green]OK Extraction complete[/green]")

    async def _setup_mcp_servers(self) -> None:
        console.print("\n[cyan]Setting up MCP servers...[/cyan]")

        default_servers = {
            "filesystem": {
                "command": "jarvis-mcp-filesystem",
                "args": ["--root", str(self.settings.project_root / "jarvis-fs")],
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
            "web_search": {
                "command": "jarvis-mcp-web-search",
            },
        }

        self.settings.mcp.servers = default_servers
        console.print("[green]OK MCP servers configured[/green]")

    def _create_config(self) -> None:
        console.print("\n[cyan]Creating configuration...[/cyan]")
        save_settings(self.settings)
        console.print(f"[green]OK Config saved to {self.settings.config_file}[/green]")

    def _add_to_path(self) -> None:
        console.print("\n[cyan]Adding to PATH...[/cyan]")

        if platform.system() == "Windows":
            jarvis_path = str(Path(sys.executable).parent / "Scripts")
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
                    console.print(f"[green]OK Added to {shell_rc}[/green]")
            else:
                console.print(f"[yellow]Add to PATH manually: {jarvis_bin}[/yellow]")


async def install() -> bool:
    installer = Installer()
    return await installer.run()


if __name__ == "__main__":
    asyncio.run(install())