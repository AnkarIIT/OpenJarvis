import asyncio

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
    assert store.get(job.job_id).output is None


def test_worker_lock_allows_only_one_owner(tmp_path):
    store = JobStore(tmp_path / "jobs.jsonl")
    with store.worker_lock() as first:
        assert first is True
        with store.worker_lock() as second:
            assert second is False
    with store.worker_lock() as third:
        assert third is True


@pytest.mark.asyncio
async def test_job_output_is_persisted(tmp_path):
    store = JobStore(tmp_path / "jobs.jsonl")
    job = AgentJob("return output")
    store.save(job)

    async def execute(_prompt):
        return "finished"

    result = await JobRunner(store, execute).run_due_once()
    assert result.status == "completed"
    assert store.get(job.job_id).output == "finished"


@pytest.mark.asyncio
async def test_lock_prevents_duplicate_execution(tmp_path):
    store = JobStore(tmp_path / "jobs.jsonl")
    job = AgentJob("one run")
    store.save(job)
    started = asyncio.Event()
    release = asyncio.Event()

    async def execute(_prompt):
        started.set()
        await release.wait()

    runner = JobRunner(store, execute)
    first = asyncio.create_task(runner.run_due_once())
    await started.wait()
    second = await runner.run_due_once()
    assert second is None
    release.set()
    assert (await first).status == "completed"
