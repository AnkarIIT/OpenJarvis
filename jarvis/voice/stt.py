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
    try:
        from vosk import Model
        return VoskSTT(settings)
    except ImportError:
        logger.warning("Vosk not available, using mock STT")
        return MockSTT(settings)