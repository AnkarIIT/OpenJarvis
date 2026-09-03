from __future__ import annotations

import platform
import psutil
from typing import Any


def get_hardware_info() -> dict[str, Any]:
    return {
        "cpu": {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            "usage_percent": psutil.cpu_percent(interval=1),
        },
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "used": psutil.virtual_memory().used,
            "percent": psutil.virtual_memory().percent,
        },
        "disk": {
            "partitions": [
                {
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total": psutil.disk_usage(p.mountpoint).total,
                    "used": psutil.disk_usage(p.mountpoint).used,
                    "free": psutil.disk_usage(p.mountpoint).free,
                }
                for p in psutil.disk_partitions()
                if p.fstype
            ]
        },
        "gpu": get_gpu_info(),
        "network": get_network_info(),
    }


def get_gpu_info() -> list[dict[str, Any]]:
    gpus = []
    try:
        import GPUtil
        for gpu in GPUtil.getGPUs():
            gpus.append({
                "id": gpu.id,
                "name": gpu.name,
                "memory_total": gpu.memoryTotal,
                "memory_used": gpu.memoryUsed,
                "memory_free": gpu.memoryFree,
                "temperature": gpu.temperature,
            })
    except ImportError:
        pass
    return gpus


def get_network_info() -> dict[str, Any]:
    return {
        "interfaces": [
            {
                "name": name,
                "addresses": [addr.address for addr in addrs],
                "stats": stats._asdict() if (stats := psutil.net_if_stats().get(name)) else None,
            }
            for name, addrs in psutil.net_if_addrs().items()
        ],
        "connections": len(psutil.net_connections()),
    }


def get_process_info(pid: int | None = None) -> dict[str, Any]:
    if pid is None:
        pid = psutil.Process().pid

    try:
        proc = psutil.Process(pid)
        return {
            "pid": proc.pid,
            "name": proc.name(),
            "cpu_percent": proc.cpu_percent(),
            "memory_info": proc.memory_info()._asdict(),
            "memory_percent": proc.memory_percent(),
            "threads": proc.num_threads(),
            "create_time": proc.create_time(),
        }
    except psutil.NoSuchProcess:
        return {}


def get_top_processes(limit: int = 10) -> list[dict[str, Any]]:
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    processes.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
    return processes[:limit]