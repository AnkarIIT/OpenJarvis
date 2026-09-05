from __future__ import annotations

import asyncio
import os
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

# Porcupine wake word model download URLs
_PORCUPINE_MODELS = {
    "jarvis": "https://github.com/Picovoice/porcupine/releases/download/v3.0.0/porcupine-3.0.0-py3-none-manylinux2014_x86_64.deb",
    "hey-jarvis": "https://huggingface.co/phatect/hey-jarvis/resolve/main/hey-jarvis_en_linux_v3_0_0/hey-jarvis.ppn",
}


def _ensure_porcupine_model(model_name: str, target_path: Path) -> bool:
    """Auto-download Porcupine .ppn file if not present."""
    if target_path.exists():
        return True

    if model_name in _PORCUPINE_MODELS:
        url = _PORCUPINE_MODELS[model_name]
        logger.info(f"Downloading Porcupine wake word model from {url}...")
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, str(target_path))
            logger.info(f"Downloaded wake word model: {target_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to download Porcupine model: {e}")
            return False

    logger.warning(
        f"Wake word model '{model_name}' not found at {target_path}. "
        f"Please run with mock wake word or download a .ppn file."
    )
    return False


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
                logger.info(f"Wake word model not found, attempting auto-download...")
                if not _ensure_porcupine_model(self.settings.voice.wake_word, self.keyword_path):
                    logger.warning(f"Wake word model not available: {self.keyword_path}")
                    return False

            access_key = os.environ.get("PORCUPINE_ACCESS_KEY", "")
            if not access_key:
                logger.warning(
                    "PORCUPINE_ACCESS_KEY not set. "
                    "Set env var PORCUPINE_ACCESS_KEY from https://console.picovoice.ai"
                )

            self.porcupine = pvporcupine.create(
                access_key=access_key,
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
            logger.info("Wake word listener started (Porcupine)")
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


class OpenWakeWordDetector:
    """Wake word detection using openWakeWord — fully open-source, no access key needed.

    Uses dscripka/openWakeWord (https://github.com/dscripka/openWakeWord).
    Models auto-download on first use.
    """

    def __init__(self, settings: Settings, callback: Callable[[], None]):
        self.settings = settings
        self.callback = callback
        self.wake_word = settings.voice.wake_word
        self.oww = None
        self.audio_stream = None
        self.running = False
        self._model = None
        self.sample_rate = 16000

    async def start(self) -> bool:
        try:
            import openwakeword
            from openwakeword.model import Model
        except ImportError:
            logger.warning("openwakeword not installed (pip install openwakeword)")
            return False

        try:
            self._model = Model()
            self.running = True

            def audio_callback(indata, frames, time, status):
                if status:
                    logger.warning(f"OpenWakeWord audio status: {status}")
                if self.running and self._model:
                    # openWakeWord expects 16kHz mono int16
                    pcm = indata[:, 0] if indata.ndim > 1 else indata
                    result = self._model.predict(pcm)
                    for model_name, score in result.items():
                        if score > 0.5:  # threshold
                            logger.info(f"Wake word detected! ({model_name}: {score})")
                            asyncio.run_coroutine_threadsafe(
                                self._trigger_callback(), asyncio.get_event_loop()
                            )

            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='int16',
                blocksize=512,
                callback=audio_callback,
            )
            self.audio_stream.start()
            logger.info("Wake word listener started (OpenWakeWord)")
            return True

        except Exception as e:
            logger.error(f"OpenWakeWord error: {e}")
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
        self._model = None
        logger.info("OpenWakeWord listener stopped")


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
    """Factory — tries engines in order of offline capability.

    1. openwakeword — fully open-source, no access key needed (RECOMMENDED)
    2. pvporcupine — requires Picoville access key + .ppn file
    3. MockWakeWord — for testing
    """
    engine = getattr(settings.voice, "wake_word_engine", "auto")

    if engine == "openwakeword" or engine == "auto":
        try:
            import openwakeword  # noqa: F401
            logger.info("Using OpenWakeWord (no access key needed)")
            return OpenWakeWordDetector(settings, callback)
        except ImportError:
            if engine == "openwakeword":
                logger.warning("OpenWakeWord not installed, falling back...")
                # Fall through to porcupine/mock

    if engine == "porcupine" or engine == "auto":
        try:
            import pvporcupine  # noqa: F401
            return PorcupineWakeWord(settings, callback)
        except ImportError:
            if engine == "porcupine":
                logger.warning("Porcupine not available, using mock wake word")
            elif engine == "auto":
                pass  # Try openwakeword next or mock

    logger.warning("No wake word engine available (install openwakeword or pvporcupine), using mock")
    return MockWakeWord(settings, callback)
