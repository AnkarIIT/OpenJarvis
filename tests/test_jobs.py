import pytest

from jarvis.agent.jobs import AgentJob, JobRunner, JobStore


def test_job_store_round_trip_and_cancel(tmp_path):
    store = JobStore(tmp_path / "jobs.jsonl")
    job = AgentJob("check status")
    store.save(job)

    assert store.get(job.job_id).prompt == "check status"
    assert store.cancel(job.job_id)
    assert store.get(job.job_id).status == "cancelled"


@pytest.mark.asyncio
async def test_job_runner_retries_then_completes(tmp_path):
    store = JobStore(tmp_path / "jobs.jsonl")
    job = AgentJob("do work", max_attempts=2)
    store.save(job)
    attempts = 0

    async def execute(prompt):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary")

    runner = JobRunner(store, execute)
    first = await runner.run_due_once()
    assert first.status == "pending"
    second = await runner.run_due_once()
    assert second.status == "completed"
    assert attempts == 2
