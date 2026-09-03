from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class PiperTTS:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.voice_model = settings.voice.tts_voice_model
        self.voice_path = self._get_voice_path()
        self.process = None

    def _get_voice_path(self) -> Path:
        config_dir = Path(os.path.expanduser("~/.jarvis/voice"))
        return config_dir / f"{self.voice_model}.onnx"

    async def speak(self, text: str) -> bool:
        if not self.voice_path.exists():
            logger.warning(f"Voice model not found: {self.voice_path}")
            return False

        try:
            cmd = [
                "piper",
                "--model", str(self.voice_path),
                "--output-raw",
            ]

            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await self.process.communicate(input=text.encode())

            if self.process.returncode != 0:
                logger.error(f"Piper TTS error: {stderr.decode()}")
                return False

            await self._play_audio(stdout)
            return True

        except Exception as e:
            logger.error(f"TTS error: {e}")
            return False

    async def _play_audio(self, audio_data: bytes) -> None:
        import sounddevice as sd
        import numpy as np

        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            sd.play(audio_array, samplerate=self.settings.voice.sample_rate)
            sd.wait()
        except Exception as e:
            logger.error(f"Audio playback error: {e}")

    async def stop(self) -> None:
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None


class MockTTS:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def speak(self, text: str) -> bool:
        logger.info(f"[MOCK TTS] {text}")
        return True

    async def stop(self) -> None:
        pass


def create_tts(settings: Settings):
    try:
        import piper
        return PiperTTS(settings)
    except ImportError:
        logger.warning("Piper not available, using mock TTS")
        return MockTTS(settings)