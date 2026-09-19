from __future__ import annotations

import asyncio
import json
import signal
import subprocess
import sys
from contextlib import suppress

import typer
from rich.console import Console

from jarvis.agent.jobs import AgentJob, JobRunner, JobStore
from jarvis.config.installer import install
from jarvis.config.settings import load_settings
from jarvis.mcp.client import MCPClient
from jarvis.skills.registry import SkillRegistry
from jarvis.skills.skill_manager import SkillManager
from jarvis.tui.app import JarvisApp
from jarvis.utils.logger import get_logger, setup_file_logging

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
    list_models: bool = typer.Option(False, "--models", "-m", help="List available LLM models from all providers"),
    pull_model: str | None = typer.Option(None, "--pull", "-p", help="Pull/download a specific model (Ollama name or GGUF URL)"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Custom config path"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
):
    """JARVIS Terminal Agent"""
    settings = load_settings(config_path)

    if list_models:
        from jarvis.utils.detectors import detect_all_local_ai, get_available_models

        all_ai = detect_all_local_ai()
        available = get_available_models()

        console.print("\n[bold cyan]Local AI Detection Results[/bold cyan]\n")
        for provider, info in all_ai.items():
            status = "[green]OK[/green]" if info["available"] else "[red]Not found[/red]"
            version = info.get("version", "N/A")
            models = info.get("models", [])
            model_list = ", ".join(models) if models else "None"
            if len(model_list) > 60:
                model_list = model_list[:57] + "..."
            version_str = str(version) if version else "N/A"
            if len(version_str) > 20:
                version_str = version_str[:17] + "..."
            console.print(f"  {provider:16} {status:20} {version_str:20} Models: {model_list}")

        console.print("\n[bold cyan]Available Models to Install[/bold cyan]\n")
        for m in available:
            if m.get("recommended"):
                tag = "[bold green][*][/bold green]" if m.get("ram_gb", 99) <= 8 else "[yellow][!][/yellow]"
                console.print(f"  {tag} {m['display']}")
        console.print("\n  Use 'jarvis --pull <model>' to download one.\n")
        return

    if pull_model:
        from jarvis.agent.llm_client import LLMClient
        client = LLMClient(settings)
        try:
            async def pull() -> None:
                async for progress in client.pull_model(pull_model):
                    if progress.strip():
                        console.print(progress.rstrip())

            asyncio.run(pull())
            console.print(f"[green]OK Model '{pull_model}' ready[/green]")
        except Exception as e:
            console.print(f"[red]ERROR Failed to pull model: {e}[/red]")
            sys.exit(1)
        return

    if install_mode:
        asyncio.run(install())
        return

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


@app.command("job-add")
def job_add(
    prompt: str = typer.Argument(..., help="Prompt for the background agent job"),
    run_at: str = typer.Option(None, "--run-at", help="UTC ISO-8601 time; runs immediately when omitted"),
    max_attempts: int = typer.Option(1, "--max-attempts", min=1, max=5),
):
    """Persist a supervised background job."""
    settings = load_settings()
    job = AgentJob(prompt=prompt, run_at=run_at, max_attempts=max_attempts)
    JobStore(settings.jobs_file).save(job)
    console.print(f"[green]Job queued:[/green] {job.job_id}")


@app.command("job-list")
def job_list():
    """List persisted background jobs."""
    settings = load_settings()
    for job in JobStore(settings.jobs_file).list():
        console.print(
            f"{job.job_id}  {job.status:9} attempts={job.attempts} "
            f"run_at={job.run_at or 'now'}  {job.prompt}"
        )


@app.command("job-cancel")
def job_cancel(job_id: str = typer.Argument(...)):
    """Cancel a pending or failed background job."""
    settings = load_settings()
    if not JobStore(settings.jobs_file).cancel(job_id):
        console.print(f"[red]Job cannot be cancelled:[/red] {job_id}")
        raise typer.Exit(1)
    console.print(f"[green]Job cancelled:[/green] {job_id}")


@app.command("job-run-once")
def job_run_once():
    """Run one due background job with normal agent safety controls."""
    settings = load_settings()

    async def run() -> AgentJob | None:
        from jarvis.agent.loop import AgentLoop

        loop = AgentLoop(settings)
        await loop.initialize()
        runner = JobRunner(
            JobStore(settings.jobs_file),
            lambda prompt: _consume_agent_run(loop, prompt),
        )
        try:
            return await runner.run_due_once()
        finally:
            await loop.mcp.disconnect_all()

    job = asyncio.run(run())
    if job is None:
        console.print("No due jobs.")
    else:
        console.print(f"Job {job.job_id}: {job.status}")


@app.command("job-worker")
def job_worker(
    poll_interval: float = typer.Option(5.0, "--poll-interval", min=0.5, help="Seconds between polls"),
):
    """Run due background jobs continuously until interrupted."""
    settings = load_settings()
    stop_event = asyncio.Event()

    def request_stop(_signum, _frame) -> None:
        stop_event.set()

    for signum in (signal.SIGINT, getattr(signal, "SIGTERM", signal.SIGINT)):
        with suppress(ValueError):
            signal.signal(signum, request_stop)

    async def run_worker() -> None:
        from jarvis.agent.loop import AgentLoop

        loop = AgentLoop(settings)
        await loop.initialize()
        runner = JobRunner(
            JobStore(settings.jobs_file),
            lambda prompt: _consume_agent_run(loop, prompt),
        )
        console.print(f"[green]JARVIS job worker running[/green] (poll={poll_interval:.1f}s)")
        try:
            while not stop_event.is_set():
                job = await runner.run_due_once()
                if job is not None:
                    console.print(f"Job {job.job_id}: {job.status}")
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=poll_interval)
                except asyncio.TimeoutError:
                    pass
        finally:
            await loop.mcp.disconnect_all()
            console.print("[yellow]JARVIS job worker stopped[/yellow]")

    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass


async def _consume_agent_run(loop, prompt: str) -> str:
    chunks: list[str] = []
    async for chunk in loop.run(prompt):
        chunks.append(chunk)
    return "".join(chunks)


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON")):
    """Check system health"""
    from rich.table import Table

    from jarvis.utils.detectors import detect_all_local_ai, get_system_info
    from jarvis.utils.health import build_health_report

    settings = load_settings()
    if json_output:
        print(json.dumps(build_health_report(settings), indent=2, default=str))
        return

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
            str(status.get("version", "N/A") or "N/A"),
            models,
        )
    console.print(table)

    sys_info = get_system_info()
    console.print(f"\n[bold]System:[/bold] {sys_info['platform']} {sys_info['platform_version']}")
    console.print(f"[bold]Python:[/bold] {sys_info['python_version'].split()[0]}")
    console.print(f"[bold]CPU:[/bold] {sys_info['cpu_count']} cores")
    console.print(f"[bold]Memory:[/bold] {sys_info['memory_total'] // (1024**3)} GB")


@app.command()
def permissions():
    """Show the current safety policy for tools and MCP servers."""
    settings = load_settings()
    console.print("[bold]JARVIS Safety Policy[/bold]")
    console.print(f"Dangerous MCP servers: {'enabled' if settings.mcp.allow_dangerous else 'disabled'}")
    console.print(
        "Enabled MCP filter: "
        + (", ".join(settings.mcp.enabled_servers) if settings.mcp.enabled_servers else "all allowed by policy")
    )
    console.print(
        f"Action confirmation: {'required' if settings.mcp.require_confirmation else 'disabled'}"
    )
    console.print(f"Action audit log: {'enabled' if settings.mcp.audit_enabled else 'disabled'}")
    console.print(f"Audit path: {settings.mcp.audit_file}")
    console.print(f"Tool policies: {len(settings.mcp.tool_policies)} configured")
    console.print(
        f"MCP calls: {settings.mcp.call_timeout:.1f}s timeout, "
        f"{settings.mcp.max_retries} retries"
    )
    console.print(f"Task state: {settings.task_state_file}")
    console.print(f"Snapshot directory: {settings.snapshot_dir}")
    console.print("To explicitly enable dangerous servers, set mcp.allow_dangerous=true in config.json.")
    console.print("Dangerous actions remain blocked until an execution confirmation interface is configured.")


@app.command()
def list_skills():
    """List all available skills with install status"""
    manager = SkillManager()
    skills = manager.list_skills()
    stats = manager.get_stats()

    from rich.table import Table
    table = Table(title="JARVIS Skills")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Category", style="yellow")
    table.add_column("Commands", style="white")
    table.add_column("Installed", style="blue")

    for skill in skills:
        cmds = ", ".join(skill["commands"][:3])
        if len(skill["commands"]) > 3:
            cmds += "..."
        table.add_row(
            skill["name"],
            skill["type"],
            skill["category"],
            cmds,
            "[green]Yes[/green]" if skill["installed"] else "[red]No[/red]",
        )
    console.print(table)
    console.print(f"\nTotal: {stats['total']} skills | {stats['installed']} installed | {stats['builtin']} builtin")


@app.command()
def install_skill(skill_name: str = typer.Argument(..., help="Name of skill to install")):
    """Install a specific skill and its dependencies"""
    manager = SkillManager()
    skill = manager.get_skill(skill_name)
    if not skill:
        console.print(f"[red]Skill '{skill_name}' not found. Use 'jarvis list-skills' to see available skills.[/red]")
        sys.exit(1)

    console.print(f"[bold]Installing {skill_name}[/bold]")
    console.print(f"Description: {skill['description']}")
    console.print(f"Commands: {', '.join(skill['commands'])}")

    deps = skill.get("dependencies", [])
    if deps:
        console.print(f"[yellow]Dependencies: {', '.join(deps)}[/yellow]")
        if not typer.confirm("Install dependencies?"):
            console.print("[yellow]Skipped.[/yellow]")
            return

    success = manager.install(skill_name)
    if success:
        console.print(f"[green]OK {skill_name} installed![/green]")
    else:
        console.print(f"[red]Failed to install {skill_name}[/red]")
        sys.exit(1)


@app.command()
def search_skills(query: str = typer.Argument(..., help="Search query")):
    """Search skills by name, description, or category"""
    manager = SkillManager()
    results = manager.search(query)

    if not results:
        console.print(f"[yellow]No skills found matching '{query}'[/yellow]")
        return

    from rich.table import Table
    table = Table(title=f"Search results for '{query}'")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Category", style="yellow")

    for skill in results:
        table.add_row(skill["name"], skill["description"][:50], skill["category"])
    console.print(table)


@app.command()
def add_skill(source: str, name: str = typer.Option(None, "--name", "-n")):
    """Add a local skill directory or clone a Git skill repository."""
    try:
        path = SkillManager().add(source, name)
        console.print(f"[green]Added skill at {path}[/green]")
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        console.print(f"[red]Failed to add skill: {exc}[/red]")
        raise typer.Exit(1)


@app.command()
def remove_skill(skill_name: str):
    """Remove a user-installed skill."""
    if SkillManager().remove(skill_name):
        console.print(f"[green]Removed skill '{skill_name}'[/green]")
    else:
        console.print(f"[yellow]User skill '{skill_name}' was not found[/yellow]")
        raise typer.Exit(1)


@app.command()
def enable_skill(skill_name: str):
    """Enable a discovered skill and persist the setting."""
    settings = load_settings()
    registry = SkillRegistry(settings)
    asyncio.run(registry.loader.discover_skills())
    if asyncio.run(registry.enable_skill(skill_name)):
        console.print(f"[green]Enabled skill '{skill_name}'[/green]")
    else:
        console.print(f"[red]Skill '{skill_name}' was not found[/red]")
        raise typer.Exit(1)


@app.command()
def disable_skill(skill_name: str):
    """Disable a discovered skill and persist the setting."""
    settings = load_settings()
    registry = SkillRegistry(settings)
    asyncio.run(registry.loader.discover_skills())
    if asyncio.run(registry.disable_skill(skill_name)):
        console.print(f"[green]Disabled skill '{skill_name}'[/green]")
    else:
        console.print(f"[red]Skill '{skill_name}' was not found[/red]")
        raise typer.Exit(1)


@app.command()
def add_mcp(name: str, command: str, args: list[str] = typer.Option([], "--arg")):
    """Register an MCP server in the persistent configuration."""
    settings = load_settings()
    try:
        MCPClient.add_server(settings, name, command, args)
        from jarvis.config.settings import save_settings
        save_settings(settings)
        console.print(f"[green]Added MCP server '{name}'[/green]")
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)


@app.command()
def remove_mcp(name: str):
    """Remove a user-configured MCP server."""
    settings = load_settings()
    if not MCPClient.remove_server(settings, name):
        console.print(f"[yellow]MCP server '{name}' was not configured[/yellow]")
        raise typer.Exit(1)
    from jarvis.config.settings import save_settings
    save_settings(settings)
    console.print(f"[green]Removed MCP server '{name}'[/green]")


@app.command()
def list_mcp():
    """List user-configured MCP servers."""
    settings = load_settings()
    servers = MCPClient.configured_servers(settings)
    if not servers:
        console.print("[yellow]No user-configured MCP servers[/yellow]")
        return
    for name, config in servers.items():
        console.print(f"{name}: {config.get('command')} {' '.join(config.get('args', []))}")


async def _list_tools() -> list[tuple[str, str]]:
    settings = load_settings()
    registry = SkillRegistry(settings)
    await registry.initialize()
    tools = [(command.name, f"skill:{command.skill_name} - {command.description}")
             for command in registry.list_commands()]
    mcp = MCPClient(settings)
    await mcp.connect_all()
    tools.extend((tool.name, f"mcp:{tool.server_name} - {tool.description}")
                 for tool in await mcp.get_available_tools())
    await mcp.disconnect_all()
    return tools


@app.command()
def list_tools():
    """List tools exposed by initialized skills and configured MCP servers."""
    try:
        tools = asyncio.run(_list_tools())
    except Exception as exc:
        console.print(f"[red]Failed to initialize tools: {exc}[/red]")
        raise typer.Exit(1)
    for name, description in tools:
        console.print(f"{name} [{description}]")


if __name__ == "__main__":
    app()
