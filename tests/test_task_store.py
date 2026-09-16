from jarvis.agent.tasks import AgentTask, TaskStore


def test_task_store_persists_and_loads_latest(tmp_path):
    store = TaskStore(tmp_path / "tasks.jsonl")
    task = AgentTask()
    task.start()
    task.finish("completed")
    store.save(task)

    loaded = store.latest()
    assert loaded is not None
    assert loaded.task_id == task.task_id
    assert loaded.status == "completed"
