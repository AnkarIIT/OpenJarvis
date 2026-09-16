import json

from jarvis.agent.audit import AuditLogger


def test_audit_logger_writes_redacted_jsonl(tmp_path):
    path = tmp_path / "audit.jsonl"
    AuditLogger(path).record(
        task_id="task-1",
        tool="run_command",
        source="mcp:terminal",
        status="blocked",
        arguments={"command": "echo hi", "api_key": "secret-value"},
        error="confirmation required",
    )

    event = json.loads(path.read_text(encoding="utf-8"))
    assert event["task_id"] == "task-1"
    assert event["status"] == "blocked"
    assert event["arguments"]["api_key"] == "[REDACTED]"
