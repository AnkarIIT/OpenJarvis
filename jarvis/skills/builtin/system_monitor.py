from __future__ import annotations

from typing import Any, Awaitable, Callable
from dataclasses import dataclass

from jarvis.skills.registry import SkillCommand
from jarvis.utils.system_info import get_hardware_info, get_top_processes
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SystemMonitorSkill:
    name: str = "system_monitor"
    description: str = "Monitor system resources (CPU, memory, disk, processes)"

    async def initialize(self, settings) -> None:
        pass

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="system_status",
                description="Get overall system status",
                handler=self._system_status,
                skill_name=self.name,
            ),
            SkillCommand(
                name="cpu_info",
                description="Get CPU information",
                handler=self._cpu_info,
                skill_name=self.name,
            ),
            SkillCommand(
                name="memory_info",
                description="Get memory information",
                handler=self._memory_info,
                skill_name=self.name,
            ),
            SkillCommand(
                name="disk_info",
                description="Get disk information",
                handler=self._disk_info,
                skill_name=self.name,
            ),
            SkillCommand(
                name="gpu_info",
                description="Get GPU information",
                handler=self._gpu_info,
                skill_name=self.name,
            ),
            SkillCommand(
                name="top_processes",
                description="Get top processes by CPU usage",
                handler=self._top_processes,
                skill_name=self.name,
            ),
        ]

    async def _system_status(self) -> str:
        info = get_hardware_info()
        return f"""System Status:
CPU: {info['cpu']['usage_percent']:.1f}% ({info['cpu']['logical_cores']} cores)
Memory: {info['memory']['percent']:.1f}% ({info['memory']['used'] // (1024**3)}GB / {info['memory']['total'] // (1024**3)}GB)
Disk: {len(info['disk']['partitions'])} partitions
GPU: {len(info['gpu'])} device(s)"""

    async def _cpu_info(self) -> str:
        info = get_hardware_info()
        cpu = info['cpu']
        return f"""CPU Information:
Usage: {cpu['usage_percent']:.1f}%
Physical Cores: {cpu['physical_cores']}
Logical Cores: {cpu['logical_cores']}
Frequency: {cpu['frequency']}"""

    async def _memory_info(self) -> str:
        info = get_hardware_info()
        mem = info['memory']
        return f"""Memory Information:
Total: {mem['total'] // (1024**3)} GB
Used: {mem['used'] // (1024**3)} GB
Available: {mem['available'] // (1024**3)} GB
Usage: {mem['percent']:.1f}%"""

    async def _disk_info(self) -> str:
        info = get_hardware_info()
        output = ["Disk Partitions:"]
        for p in info['disk']['partitions']:
            output.append(f"  {p['mountpoint']} ({p['fstype']}): {p['free'] // (1024**3)} GB free of {p['total'] // (1024**3)} GB")
        return "\n".join(output)

    async def _gpu_info(self) -> str:
        info = get_hardware_info()
        if not info['gpu']:
            return "No GPU detected"
        output = ["GPU Information:"]
        for gpu in info['gpu']:
            output.append(f"  {gpu['name']}: {gpu['memory_used']}MB / {gpu['memory_total']}MB, Temp: {gpu['temperature']}°C")
        return "\n".join(output)

    async def _top_processes(self, limit: int = 10) -> str:
        processes = get_top_processes(limit)
        output = [f"Top {limit} Processes by CPU:"]
        for i, p in enumerate(processes, 1):
            output.append(f"  {i}. {p['name']} (PID: {p['pid']}) - CPU: {p['cpu_percent']:.1f}%, Mem: {p['memory_percent']:.1f}%")
        return "\n".join(output)