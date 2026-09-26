"""
martian_device.py — Martian Device API Server (Full Featured)
Run: python martian_device.py api

Endpoints:
  GET  /health                 — server health
  GET  /device                 — device state
  POST /device                 — update device state
  GET  /telemetry              — latest sensor readings + history
  GET  /telemetry/stream       — SSE live telemetry stream
  GET  /logs                   — device activity logs (filterable)
  POST /config                 — update device config
  GET  /config                 — current config
  GET  /jobs                   — job list (filterable by status)
  POST /jobs                   — create job
  POST /jobs/<id>/complete     — mark job complete + store result
  DELETE /jobs/<id>            — cancel job
  POST /jarvis/ping            — Jarvis ↔ device integration
  POST /jarvis/command         — Jarvis command execution
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone

from flask import Flask, jsonify, request, Response

app = Flask(__name__)

# ── Device State ──────────────────────────────────────────────────────────────
_device_state = {
    "device_id": "martian-001",
    "status": "offline",
    "battery": 100.0,
    "temperature": 22.0,
    "humidity": 45.0,
    "pressure": 1013.25,
    "signal_strength": 95,
    "last_heartbeat": None,
    "memory_usage": 0,
    "cpu_usage": 0,
    "disk_usage": 0,
    "jobs": [],
}

# ── Device Config ─────────────────────────────────────────────────────────────
_device_config = {
    "location": "Mars Surface — Jezero Crater",
    "mode": "autonomous",
    "sampling_rate_hz": 10,
    "power_saving": False,
    "sensor_mask": ["temperature", "humidity", "pressure", "signal"],
    "max_jobs": 50,
    "log_retention_hours": 24,
}

# ── Logs ──────────────────────────────────────────────────────────────────────
MAX_LOGS = 500
_device_logs: deque = deque(maxlen=MAX_LOGS)


def _log(level: str, message: str, **meta):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        **meta,
    }
    _device_logs.append(entry)
    return entry


# ── Telemetry History ─────────────────────────────────────────────────────────
MAX_TELEMETRY = 200
_telemetry_history: deque = deque(maxlen=MAX_TELEMETRY)


def _push_telemetry():
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": _device_state["temperature"],
        "humidity": _device_state["humidity"],
        "pressure": _device_state["pressure"],
        "battery": _device_state["battery"],
        "signal_strength": _device_state["signal_strength"],
        "cpu_usage": _device_state["cpu_usage"],
        "memory_usage": _device_state["memory_usage"],
    }
    _telemetry_history.append(entry)
    return entry


# ── Background Threads ────────────────────────────────────────────────────────
_stop_event = threading.Event()
_heartbeat_thread: threading.Thread | None = None
_simulate_thread: threading.Thread | None = None


def _heartbeat_loop():
    """Update heartbeat + lightweight metrics every 5s."""
    while not _stop_event.is_set():
        _device_state["last_heartbeat"] = time.time()
        _device_state["memory_usage"] = 25 + int((time.time() % 6) * 8)
        _device_state["cpu_usage"] = 10 + int((time.time() % 4) * 15)
        _device_state["disk_usage"] = 40 + int((time.time() % 10) * 5)
        _log("info", "heartbeat", battery=_device_state["battery"])
        time.sleep(5)


def _simulate_loop():
    """Simulate sensor readings + battery drain every 2s."""
    t0 = time.time()
    while not _stop_event.is_set():
        elapsed = time.time() - t0
        _device_state["temperature"] = 22.0 + (elapsed % 12) * 0.4 + (time.time() % 3) * 0.1
        _device_state["humidity"] = 45.0 - (elapsed % 8) * 2.0
        _device_state["pressure"] = 1013.25 + (time.time() % 20) * 0.5
        _device_state["battery"] = max(5.0, 100.0 - elapsed * 0.005)
        _device_state["signal_strength"] = max(20, 95 - int((time.time() % 30) * 2.5))
        _push_telemetry()
        _log("debug", "telemetry updated",
             temperature=_device_state["temperature"],
             humidity=_device_state["humidity"])
        time.sleep(2)


# ── Notification hook (called on state changes — can be overridden) ───────────
_notification_listeners: list = []


def _notify(event: str, data: dict):
    """Fire notification to all registered listeners (e.g. Jarvis integration)."""
    for cb in _notification_listeners:
        try:
            cb(event, data)
        except Exception:
            pass  # one bad listener must not break others


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "device": _device_state["device_id"],
        "api_version": "1.0.0",
        "uptime": time.time() - (_device_state.get("_start_time", time.time())),
    })


@app.route("/device", methods=["GET"])
def get_device():
    return jsonify(dict(_device_state))


@app.route("/device", methods=["POST"])
def set_device():
    data = request.get_json(force=True, silent=True) or {}
    changed = []
    for key in ("status", "battery", "temperature", "humidity",
                "pressure", "signal_strength", "memory_usage", "cpu_usage", "disk_usage"):
        if key in data:
            _device_state[key] = data[key]
            changed.append(key)
    _log("info", "device state updated", changes=changed)
    _notify("device_update", dict(_device_state))
    return jsonify({"success": True, "device": dict(_device_state)})


@app.route("/telemetry", methods=["GET"])
def get_telemetry():
    if not _telemetry_history:
        return jsonify({"telemetry": [], "count": 0})
    return jsonify({
        "telemetry": list(_telemetry_history),
        "count": len(_telemetry_history),
        "latest": _telemetry_history[-1],
    })


@app.route("/telemetry/stream", methods=["GET"])
def telemetry_stream():
    """Server-Sent Events: live telemetry snapshot every 2s."""
    def generate():
        if _telemetry_history:
            yield f"data: {json.dumps(_telemetry_history[-1])}\n\n"
        while not _stop_event.is_set():
            if _telemetry_history:
                yield f"data: {json.dumps(_telemetry_history[-1])}\n\n"
            time.sleep(2)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/logs", methods=["GET"])
def get_logs():
    level = request.args.get("level", "")
    limit = request.args.get("limit", 100, type=int)
    logs = list(_device_logs)
    if level:
        logs = [l for l in logs if l["level"] == level]
    logs = logs[-limit:]
    return jsonify({
        "logs": logs,
        "count": len(logs),
        "total_available": len(_device_logs),
    })


@app.route("/config", methods=["GET"])
def get_config():
    return jsonify({"config": dict(_device_config)})


@app.route("/config", methods=["POST"])
def set_config():
    data = request.get_json(force=True, silent=True) or {}
    changed = []
    for key in ("location", "mode", "sampling_rate_hz", "power_saving",
                "sensor_mask", "max_jobs", "log_retention_hours"):
        if key in data:
            _device_config[key] = data[key]
            changed.append(key)
    _log("info", "config updated", config=_device_config, changes=changed)
    _notify("config_update", dict(_device_config))
    return jsonify({"success": True, "config": dict(_device_config)})


@app.route("/jobs", methods=["GET"])
def list_jobs():
    status_filter = request.args.get("status", "")
    jobs = _device_state["jobs"]
    if status_filter:
        jobs = [j for j in jobs if j["status"] == status_filter]
    return jsonify({"jobs": jobs, "count": len(jobs)})


@app.route("/jobs", methods=["POST"])
def create_job():
    data = request.get_json(force=True, silent=True) or {}
    if len(_device_state["jobs"]) >= _device_config["max_jobs"]:
        return jsonify({"error": "max jobs reached", "max": _device_config["max_jobs"]}), 409
    job = {
        "id": f"job-{len(_device_state['jobs']) + 1:03d}",
        "task": data.get("task", "unknown"),
        "priority": data.get("priority", "normal"),
        "parameters": data.get("parameters", {}),
        "status": "pending",
        "created_at": time.time(),
    }
    _device_state["jobs"].append(job)
    _log("info", "job created", job_id=job["id"], task=job["task"])
    _notify("job_created", job)
    return jsonify({"success": True, "job": job}), 201


@app.route("/jobs/<job_id>/complete", methods=["POST"])
def complete_job(job_id):
    for job in _device_state["jobs"]:
        if job["id"] == job_id:
            job["status"] = "completed"
            job["completed_at"] = time.time()
            job["result"] = request.get_json(force=True, silent=True) or {}
            _log("info", "job completed", job_id=job_id)
            _notify("job_completed", job)
            return jsonify({"success": True, "job": job})
    return jsonify({"error": "job not found"}), 404


@app.route("/jobs/<job_id>", methods=["DELETE"])
def cancel_job(job_id):
    before = len(_device_state["jobs"])
    _device_state["jobs"] = [j for j in _device_state["jobs"] if j["id"] != job_id]
    if before - len(_device_state["jobs"]) > 0:
        _log("info", "job canceled", job_id=job_id)
        _notify("job_canceled", {"job_id": job_id})
        return jsonify({"success": True, "canceled": True})
    return jsonify({"success": False, "canceled": False, "error": "job not found"}), 404


@app.route("/jarvis/ping", methods=["POST"])
def jarvis_ping():
    """Jarvis → device: message receive + ack."""
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "ping")
    _log("info", "jarvis ping received", message=message)
    _notify("jarvis_ping", {
        "device": _device_state["device_id"],
        "received": message,
        "device_status": _device_state["status"],
        "timestamp": time.time(),
    })
    return jsonify({
        "device": _device_state["device_id"],
        "received": message,
        "device_status": _device_state["status"],
        "timestamp": time.time(),
        "reply": f"Martian device received: {message}",
    })


@app.route("/jarvis/command", methods=["POST"])
def jarvis_command():
    """Jarvis → device: command execution."""
    data = request.get_json(force=True, silent=True) or {}
    cmd = data.get("command", "")
    params = data.get("parameters", {})
    _device_state["status"] = "active"
    _log("info", "jarvis command executed", command=cmd, params=params)
    _notify("jarvis_command", {"command": cmd, "status": "active"})
    return jsonify({
        "success": True,
        "executed": cmd,
        "device_status": _device_state["status"],
        "parameters_applied": params,
    })


# ── CLI ───────────────────────────────────────────────────────────────────────
def run_server(host="0.0.0.0", port=5000):
    _stop_event.clear()
    _device_state["_start_time"] = time.time()
    _device_state["status"] = "online"
    _log("info", "server starting", host=host, port=port)

    _heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    _heartbeat_thread.start()

    _simulate_thread = threading.Thread(target=_simulate_loop, daemon=True)
    _simulate_thread.start()

    _push_telemetry()
    print(f"[martian_device] API server running  → http://{host}:{port}")
    print(f"[martian_device] Device ID           → {_device_state['device_id']}")
    print(f"[martian_device] SSE Telemetry       → http://{host}:{port}/telemetry/stream")
    print(f"[martian_device] Press Ctrl+C to stop")
    app.run(host=host, port=port, debug=False)


def main():
    parser = argparse.ArgumentParser(description="Martian Device API Server")
    sub = parser.add_subparsers(dest="command")

    api_cmd = sub.add_parser("api", help="Run the API server")
    api_cmd.add_argument("--host", default="0.0.0.0")
    api_cmd.add_argument("--port", type=int, default=5000)

    args = parser.parse_args()
    if args.command == "api":
        run_server(host=args.host, port=args.port)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
