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


class SarvamTTS:
    """TTS using Sarvam AI (Bulbul v3/v2). https://docs.sarvam.ai"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_key = settings.voice.sarvam_api_key
        self.model = settings.voice.sarvam_tts_model
        self.speaker = settings.voice.sarvam_tts_speaker
        self.pace = settings.voice.sarvam_tts_pace
        self.temperature = settings.voice.sarvam_tts_temperature if hasattr(settings.voice, "sarvam_tts_temperature") else 0.6
        self.language_code = settings.voice.language
        self.sample_rate = settings.voice.sample_rate
        self._process: Optional[asyncio.subprocess.Process] = None

    async def speak(self, text: str) -> bool:
        if not self.api_key:
            logger.warning("Sarvam TTS: API key not set")
            return False

        import aiohttp
        import base64
        import io

        try:
            url = "https://api.sarvam.ai/text-to-speech"
            headers = {"api-subscription-key": self.api_key, "Content-Type": "application/json"}
            payload = {
                "text": text,
                "language_code": self.language_code,
                "model": self.model,
                "speaker": self.speaker,
                "pace": self.pace,
                "temperature": self.temperature,
                "speech_sample_rate": self.sample_rate,
                "enable_preprocessing": True,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"Sarvam TTS error: {resp.status} {await resp.text()}")
                        return False
                    data = await resp.json()

            audios = data.get("audios", [])
            if not audios:
                logger.error("Sarvam TTS: no audio returned")
                return False

            audio_bytes = base64.b64decode(audios[0])

            # Sarvam returns WAV data; play it directly
            await self._play_wav(audio_bytes)
            return True

        except ImportError:
            logger.warning("aiohttp not available for Sarvam TTS")
            return False
        except Exception as e:
            logger.error(f"Sarvam TTS error: {e}")
            return False

    async def _play_wav(self, wav_data: bytes) -> None:
        """Play WAV audio data using sounddevice."""
        import sounddevice as sd
        import numpy as np
        
        import io as io_module

        try:
            import wave as wave_module
            with wave_module.open(file=io_module.BytesIO(wav_data), mode='rb') as wf:
                frames = wf.readframes(-1)
                rate = wf.getframerate()
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()

            dtype = None
            if sample_width == 1:
                dtype = np.uint8
            elif sample_width == 2:
                dtype = np.int16
            elif sample_width == 4:
                dtype = np.int32
            else:
                logger.warning(f"Unsupported sample width: {sample_width}")
                return

            audio_array = np.frombuffer(frames, dtype=dtype)
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels)

            sd.play(audio_array, samplerate=rate)
            sd.wait()
        except Exception as e:
            logger.error(f"Sarvam audio playback error: {e}")

    async def stop(self) -> None:
        pass


class MockTTS:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def speak(self, text: str) -> bool:
        logger.info(f"[MOCK TTS] {text}")
        return True

    async def stop(self) -> None:
        pass


def create_tts(settings: Settings):
    engine = settings.voice.tts_engine
    if engine == "sarvam":
        return SarvamTTS(settings)
    try:
        import piper
        return PiperTTS(settings)
    except ImportError:
        if engine == "piper":
            logger.warning("Piper not available, using mock TTS")
        return MockTTS(settings)