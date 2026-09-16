import pytest

from jarvis.agent.loop import AgentLoop
from jarvis.agent.tasks import AgentTask
from jarvis.config.settings import Settings


@pytest.mark.asyncio
async def test_agent_run_records_completed_task(monkeypatch):
    loop = AgentLoop(Settings())

    async def fake_run(user_input, voice_mode=False):
        yield "done"

    monkeypatch.setattr(loop, "_run", fake_run)
    chunks = [chunk async for chunk in loop.run("hello")]

    assert chunks == ["done"]
    assert loop.last_task is not None
    assert loop.last_task.status == "completed"
    assert loop.last_task.task_id


def test_agent_task_records_phases():
    task = AgentTask()
    task.add_step("plan", "select tools")
    task.add_step("execute", "run tool")
    task.add_step("verify", "check result")
    assert [step["phase"] for step in task.steps] == ["plan", "execute", "verify"]


@pytest.mark.asyncio
async def test_agent_run_records_failed_task(monkeypatch):
    loop = AgentLoop(Settings())

    async def fake_run(user_input, voice_mode=False):
        raise RuntimeError("provider failed")
        yield ""

    monkeypatch.setattr(loop, "_run", fake_run)
    with pytest.raises(RuntimeError, match="provider failed"):
        [chunk async for chunk in loop.run("hello")]

    assert loop.last_task is not None
    assert loop.last_task.status == "failed"
    assert loop.last_task.error == "provider failed"
