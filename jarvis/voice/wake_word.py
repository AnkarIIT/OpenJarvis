from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Callable, Optional

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class PorcupineWakeWord:
    def __init__(self, settings: Settings, callback: Callable[[], None]):
        self.settings = settings
        self.callback = callback
        self.keyword_path = self._get_keyword_path()
        self.porcupine = None
        self.audio_stream = None
        self.running = False

    def _get_keyword_path(self) -> Path:
        config_dir = Path(os.path.expanduser("~/.jarvis/voice"))
        return config_dir / f"{self.settings.voice.wake_word}.ppn"

    async def start(self) -> bool:
        try:
            import pvporcupine
            import sounddevice as sd

            if not self.keyword_path.exists():
                logger.warning(f"Wake word model not found: {self.keyword_path}")
                return False

            self.porcupine = pvporcupine.create(
                access_key=os.environ.get("PORCUPINE_ACCESS_KEY", ""),
                keyword_paths=[str(self.keyword_path)],
            )

            self.running = True

            def audio_callback(indata, frames, time, status):
                if status:
                    logger.warning(f"Wake word audio status: {status}")
                if self.running and self.porcupine:
                    pcm = indata[:, 0] if indata.ndim > 1 else indata
                    keyword_index = self.porcupine.process(pcm)
                    if keyword_index >= 0:
                        logger.info("Wake word detected!")
                        asyncio.run_coroutine_threadsafe(self._trigger_callback(), asyncio.get_event_loop())

            self.audio_stream = sd.InputStream(
                samplerate=self.porcupine.sample_rate,
                blocksize=self.porcupine.frame_length,
                dtype='int16',
                channels=1,
                callback=audio_callback,
            )
            self.audio_stream.start()
            logger.info("Wake word listener started")
            return True

        except ImportError:
            logger.warning("Porcupine not available")
            return False
        except Exception as e:
            logger.error(f"Wake word error: {e}")
            return False

    async def _trigger_callback(self) -> None:
        try:
            await self.callback()
        except Exception as e:
            logger.error(f"Wake word callback error: {e}")

    async def stop(self) -> None:
        self.running = False
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None
        logger.info("Wake word listener stopped")


class MockWakeWord:
    def __init__(self, settings: Settings, callback: Callable[[], None]):
        self.settings = settings
        self.callback = callback
        self.running = False

    async def start(self) -> bool:
        self.running = True
        logger.info("[MOCK] Wake word listener started")
        return True

    async def stop(self) -> None:
        self.running = False
        logger.info("[MOCK] Wake word listener stopped")


def create_wake_word(settings: Settings, callback: Callable[[], None]):
    try:
        import pvporcupine
        return PorcupineWakeWord(settings, callback)
    except ImportError:
        logger.warning("Porcupine not available, using mock wake word")
        return MockWakeWord(settings, callback)