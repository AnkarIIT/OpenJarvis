from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class InstantLearningSkill:
    name: str = "instant_learning"
    description: str = "Learn instantly from examples, few-shot prompts, and feedback."
    version: str = "1.0.0"
    author: str = "OpenJarvis"

    def __init__(self, settings=None):
        self.settings = settings
        self.examples: dict[str, list[dict]] = {}  # task -> examples
        self.fine_tuned: dict[str, Any] = {}  # model_name -> fine-tuned weights info

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="learn_example",
                description="Teach a new task with examples. Usage: learn_example --task coding --input 'x=1,y=2' --output '3'",
                handler=self._teach,
                skill_name=self.name,
            ),
            SkillCommand(
                name="learn_few_shot",
                description="Provide few-shot examples for a task.",
                handler=self._few_shot,
                skill_name=self.name,
            ),
            SkillCommand(
                name="learn_fine_tune",
                description="Fine-tune a model on provided data.",
                handler=self._fine_tune,
                skill_name=self.name,
            ),
            SkillCommand(
                name="learn_list_tasks",
                description="List all learned tasks and their example counts.",
                handler=self._list_tasks,
                skill_name=self.name,
            ),
            SkillCommand(
                name="learn_infer",
                description="Apply learned patterns to new input.",
                handler=self._infer,
                skill_name=self.name,
            ),
            SkillCommand(
                name="learn_forget",
                description="Remove learned examples for a task.",
                handler=self._forget,
                skill_name=self.name,
            ),
        ]

    async def initialize(self, settings) -> None:
        self.settings = settings

    async def _teach(self, task: str = "", input_data: str = "", output: str = "") -> str:
        if not task or not input_data or not output:
            return "Error: --task, --input, --output all required"

        if task not in self.examples:
            self.examples[task] = []

        self.examples[task].append({"input": input_data, "output": output})

        return (
            f"Learned: '{task}' example added.\n"
            f"Task now has {len(self.examples[task])} example(s)."
        )

    async def _few_shot(self, task: str = "", examples_json: str = "") -> str:
        if not task:
            return "Error: --task is required"

        try:
            examples = json.loads(examples_json) if examples_json else []
        except json.JSONDecodeError:
            return "Error: Invalid JSON in --examples_json"

        if task not in self.examples:
            self.examples[task] = []
        self.examples[task].extend(examples)

        return f"Added {len(examples)} few-shot examples to task '{task}'. Total: {len(self.examples[task])}"

    async def _fine_tune(self, task: str = "", model_name: str = "llama3.1:8b") -> str:
        if not task:
            return "Error: --task is required"

        if task not in self.examples or len(self.examples[task]) < 2:
            return f"Error: Need at least 2 examples for '{task}'. Have {len(self.examples.get(task, []))}"

        # In a real implementation, this would:
        # 1. Use LoRA/QLoRA to fine-tune the model
        # 2. Save the adapter weights
        # 3. Create a merged model
        # For now, simulate the process
        self.fine_tuned[task] = {
            "model": model_name,
            "examples": len(self.examples[task]),
            "status": "fine_tuned",
            "method": "LoRA",
        }

        return (
            f"Fine-tuning '{task}' on {model_name}...\n"
            f"Method: LoRA | Examples: {len(self.examples[task])}\n"
            f"Status: Simulated fine-tune complete. In production, use: accelerate+peft for real fine-tuning."
        )

    async def _list_tasks(self) -> str:
        if not self.examples:
            return "No learned tasks yet"
        lines = ["Learned Tasks:"]
        for task, examples in self.examples.items():
            ft = "✓ Fine-tuned" if task in self.fine_tuned else "○ Examples only"
            lines.append(f"  {task}: {len(examples)} examples {ft}")
        return "\n".join(lines)

    async def _infer(self, task: str = "", input_data: str = "") -> str:
        if task not in self.examples:
            return f"Error: Task '{task}' not learned. Use: learn_example first"

        examples = self.examples[task]

        # Build a few-shot prompt for the LLM
        prompt = f"Task: {task}\n\nExamples:\n"
        for ex in examples:
            prompt += f"  Input: {ex['input']}\n  Output: {ex['output']}\n"
        prompt += f"\nInput: {input_data}\nOutput:"

        return f"Few-shot prompt built ({len(examples)} examples). Pass this to the LLM for inference.\n\n{prompt}"

    async def _forget(self, task: str = "") -> str:
        if task in self.examples:
            count = len(self.examples[task])
            del self.examples[task]
            self.fine_tuned.pop(task, None)
            return f"Forgot task '{task}' ({count} examples removed)"
        return f"Task '{task}' not found"
