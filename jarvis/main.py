from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console

from jarvis.config.settings import load_settings, Settings
from jarvis.config.installer import install
from jarvis.tui.app import JarvisApp
from jarvis.utils.logger import setup_file_logging, get_logger

logger = get_logger(__name__)
console = Console()

app = typer.Typer(
    name="jarvis",
    help="JARVIS - Just A Rather Very Intelligent System",
    add_completion=False,
)


@app.command()
def main(
    install_mode: bool = typer.Option(False, "--install", "-i", help="Run installer"),
    config_path: str = typer.Option(None, "--config", "-c", help="Custom config path"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
):
    """JARVIS Terminal Agent"""
    if install_mode:
        asyncio.run(install())
        return

    settings = load_settings()

    if config_path:
        settings.config_file = Path(config_path).expanduser()

    setup_file_logging(settings.config_dir)

    if debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    # Check if first run (no config or no model configured)
    if not settings.config_file.exists() or not settings.llm.model:
        console.print("[yellow]First run detected. Starting setup...[/yellow]\n")
        success = asyncio.run(install())
        if not success:
            console.print("[red]Setup failed. Run 'jarvis --install' to retry.[/red]")
            sys.exit(1)
        # Reload settings after install
        settings = load_settings()

    console.print("[bold cyan]JARVIS[/bold cyan] - Starting...")
    console.print(f"Model: {settings.llm.model} ({settings.llm.provider})")
    console.print(f"Voice: {'Enabled' if settings.voice.enabled else 'Disabled'}")
    console.print(f"Memory: {'Enabled' if settings.memory.enabled else 'Disabled'}")

    try:
        jarvis_app = JarvisApp(settings)
        jarvis_app.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]JARVIS shutting down...[/yellow]")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@app.command()
def setup():
    """Run first-time setup"""
    asyncio.run(install())


@app.command()
def doctor():
    """Check system health"""
    from jarvis.utils.detectors import detect_all_local_ai, get_system_info
    from rich.table import Table

    console.print("[bold]JARVIS System Diagnostics[/bold]\n")

    ai_status = detect_all_local_ai()
    table = Table(title="Local AI Detection")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Version", style="yellow")
    table.add_column("Models", style="white")

    for provider, status in ai_status.items():
        models = ", ".join(status.get("models", [])) if status.get("models") else "None"
        if len(models) > 40:
            models = models[:37] + "..."
        table.add_row(
            provider.replace("_", " ").title(),
            "OK Available" if status["available"] else "ERROR Not found",
            status.get("version", "N/A"),
            models,
        )
    console.print(table)

    sys_info = get_system_info()
    console.print(f"\n[bold]System:[/bold] {sys_info['platform']} {sys_info['platform_version']}")
    console.print(f"[bold]Python:[/bold] {sys_info['python_version'].split()[0]}")
    console.print(f"[bold]CPU:[/bold] {sys_info['cpu_count']} cores")
    console.print(f"[bold]Memory:[/bold] {sys_info['memory_total'] // (1024**3)} GB")


if __name__ == "__main__":
    app()