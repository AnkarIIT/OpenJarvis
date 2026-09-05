from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

import sounddevice as sd
import numpy as np

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class VoskSTT:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_path = self._get_model_path()
        self.model = None
        self.recognizer = None
        self.sample_rate = settings.voice.sample_rate
        self._init_model()

    def _get_model_path(self) -> Path:
        config_dir = Path(os.path.expanduser("~/.jarvis/voice"))
        return config_dir / self.settings.voice.stt_model

    def _init_model(self) -> None:
        try:
            from vosk import Model, KaldiRecognizer
            if self.model_path.exists():
                self.model = Model(str(self.model_path))
                self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
                logger.info("Vosk STT model loaded")
            else:
                logger.warning(f"Vosk model not found: {self.model_path}")
        except ImportError:
            logger.warning("Vosk not available")

    async def listen_once(self, timeout: float = 10.0) -> str:
        if not self.recognizer:
            return ""

        try:
            audio_queue = asyncio.Queue()

            def callback(indata, frames, time, status):
                if status:
                    logger.warning(f"Audio callback status: {status}")
                asyncio.run_coroutine_threadsafe(audio_queue.put(bytes(indata)), asyncio.get_event_loop())

            stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=4000,
                dtype='int16',
                channels=1,
                callback=callback,
            )

            with stream:
                logger.info("Listening...")
                start_time = asyncio.get_event_loop().time()

                while asyncio.get_event_loop().time() - start_time < timeout:
                    try:
                        data = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                        if self.recognizer.AcceptWaveform(data):
                            result = json.loads(self.recognizer.Result())
                            text = result.get("text", "").strip()
                            if text:
                                logger.info(f"Heard: {text}")
                                return text
                        else:
                            partial = json.loads(self.recognizer.PartialResult())
                            partial_text = partial.get("partial", "")
                            if partial_text:
                                pass
                    except asyncio.TimeoutError:
                        continue

                final = json.loads(self.recognizer.FinalResult())
                return final.get("text", "").strip()

        except Exception as e:
            logger.error(f"STT error: {e}")
            return ""

    async def start_streaming(self, callback) -> None:
        pass

    async def stop_streaming(self) -> None:
        pass


class SarvamSTT:
    """STT using Sarvam AI (Saaras v3/v4). https://docs.sarvam.ai"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_key = settings.voice.sarvam_api_key
        self.model = settings.voice.sarvam_stt_model
        self.language_code = settings.voice.language
        self.sample_rate = settings.voice.sample_rate
        self._stream_task: Optional[asyncio.Task] = None
        self._listening = False

    async def _record_audio(self, duration: float) -> bytes:
        """Record audio from microphone for a fixed duration."""
        import sounddevice as sd
        import numpy as np

        frames = []

        def callback(indata, frames_count, time, status):
            if status:
                logger.warning(f"Audio callback status: {status}")
            frames.append(bytes(indata))

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                callback=callback,
            ):
                logger.info("Recording...")
                await asyncio.sleep(duration)
            audio_bytes = b"".join(frames)

            # Convert to WAV
            import wave
            import io as io_module
            buf = io_module.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_bytes)
            return buf.getvalue()
        except Exception as e:
            logger.error(f"Audio recording error: {e}")
            return b""

    async def listen_once(self, timeout: float = 10.0) -> str:
        if not self.api_key:
            logger.warning("Sarvam STT: API key not set")
            return ""

        import aiohttp

        try:
            # Record audio
            audio_data = await self._record_audio(min(timeout, 10.0))
            if not audio_data:
                return ""

            url = "https://api.sarvam.ai/speech-to-text"
            headers = {"api-subscription-key": self.api_key}

            form = aiohttp.FormData()
            form.add_field("file", audio_data, filename="audio.wav", content_type="audio/wav")
            form.add_field("model", self.model)
            if self.settings.voice.language_detection:
                form.add_field("language_code", "unknown")
            else:
                form.add_field("language_code", self.language_code)

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=form, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"Sarvam STT error: {resp.status} {await resp.text()}")
                        return ""
                    result = await resp.json()

            transcript = result.get("transcript", "").strip()
            detected_lang = result.get("language_code")
            if detected_lang and self.settings.voice.language_detection:
                # Update language for TTS response
                self.language_code = detected_lang
                self.settings.voice.language = detected_lang

            if transcript:
                logger.info(f"Heard: {transcript} (language: {detected_lang})")
            return transcript

        except ImportError:
            logger.warning("aiohttp not available for Sarvam STT")
            return ""
        except Exception as e:
            logger.error(f"Sarvam STT error: {e}")
            return ""

    async def start_streaming(self, callback) -> None:
        pass

    async def stop_streaming(self) -> None:
        pass


class MockSTT:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def listen_once(self, timeout: float = 10.0) -> str:
        logger.info("[MOCK STT] Waiting for input...")
        await asyncio.sleep(1)
        return "Hello JARVIS"

    async def start_streaming(self, callback) -> None:
        pass

    async def stop_streaming(self) -> None:
        pass


def create_stt(settings: Settings):
    engine = settings.voice.stt_engine
    if engine == "sarvam":
        return SarvamSTT(settings)
    try:
        from vosk import Model
        return VoskSTT(settings)
    except ImportError:
        if engine == "vosk":
            logger.warning("Vosk not available, using mock STT")
        return MockSTT(settings)