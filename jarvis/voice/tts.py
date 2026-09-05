from __future__ import annotations

import asyncio
import os
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

# Known Piper voice models for auto-download
_PIPER_VOICES = {
    "en_US-lessac-medium": "en_US-lessac-medium.onnx",
    "en_US-amy-low": "en_US-amy-low.onnx",
    "en_US-libritts-high": "en_US-libritts-high.onnx",
    "hi_IN-ins-kitu-medium": "hi_IN-ins-kitu-medium.onnx",
}

# Piper model download base URLs (hosted on GitHub releases)
_PIPER_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


async def _ensure_piper_model(voice_name: str, onnx_path: Path, config_path: Path) -> bool:
    """Auto-download a Piper voice model if not present."""
    if onnx_path.exists() and config_path.exists():
        return True

    if voice_name not in _PIPER_VOICES:
        logger.error(f"Unknown Piper voice: {voice_name}. Available: {list(_PIPER_VOICES.keys())}")
        return False

    onnx_filename = _PIPER_VOICES[voice_name]
    config_filename = os.path.basename(onnx_filename).replace(".onnx", ".onnx.json")

    # Try downloading from HuggingFace mirror
    urls = [
        f"{_PIPER_BASE_URL}/en/US/lessac/medium/{onnx_filename}",
        f"https://github.com/rhasspy/piper/releases/download/v2021.258/{onnx_filename}",
    ]

    for url in urls:
        try:
            logger.info(f"Downloading Piper voice model from {url}...")
            onnx_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, str(onnx_path))

            # Download config JSON
            config_url = url.replace(".onnx", ".onnx.json")
            urllib.request.urlretrieve(config_url, str(config_path))
            logger.info(f"Downloaded Piper voice: {onnx_path}")
            return True
        except Exception as e:
            logger.warning(f"Download failed from {url}: {e}")
            continue

    logger.error(f"Could not auto-download Piper voice: {voice_name}")
    return False


class PiperTTS:
    """TTS using the piper-tts Python package (no CLI binary required)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.voice_model = settings.voice.tts_voice_model
        self.voice_path = self._get_voice_path()
        self.config_path = self.voice_path.with_suffix(".onnx.json")
        self._piper_voice = None
        self._voice_loaded = False

    def _get_voice_path(self) -> Path:
        config_dir = Path(os.path.expanduser("~/.jarvis/voice"))
        return config_dir / f"{self.voice_model}.onnx"

    async def _ensure_voice(self) -> bool:
        """Lazy-load the Piper voice, downloading if necessary."""
        if self._voice_loaded:
            return self._piper_voice is not None

        try:
            from piper.voice import PiperVoice
        except ImportError:
            logger.warning(
                "piper-tts package not installed. "
                "Install with: pip install piper-tts"
            )
            self._voice_loaded = True
            return False

        if not self.voice_path.exists() or not self.config_path.exists():
            logger.info(f"Piper voice not found at {self.voice_path}, attempting auto-download...")
            await _ensure_piper_model(self.voice_model, self.voice_path, self.config_path)

        if not self.voice_path.exists():
            logger.warning(f"Piper voice model not available: {self.voice_path}")
            self._voice_loaded = True
            return False

        try:
            self._piper_voice = PiperVoice.load(
                str(self.voice_path),
                str(self.config_path) if self.config_path.exists() else None,
            )
            logger.info(f"Piper TTS loaded: {self.voice_model}")
        except Exception as e:
            logger.error(f"Piper voice init error: {e}")

        self._voice_loaded = True
        return self._piper_voice is not None

    async def speak(self, text: str) -> bool:
        if not await self._ensure_voice():
            logger.warning("Piper voice not initialized")
            return False

        try:
            import numpy as np
            import sounddevice as sd

            # Generate audio synchronously (piper is CPU-bound but fast)
            audio_data = bytearray()

            def _generate():
                for chunk in self._piper_voice.synthesize(text, self._piper_voice):
                    audio_data.extend(chunk)

            await asyncio.get_event_loop().run_in_executor(None, _generate)

            if not audio_data:
                logger.error("Piper TTS: no audio generated")
                return False

            # Play via sounddevice
            audio_array = np.frombuffer(bytes(audio_data), dtype=np.int16)
            sample_rate = self._piper_voice.config.sample_rate
            sd.play(audio_array, samplerate=sample_rate)
            sd.wait()
            return True

        except Exception as e:
            logger.error(f"Piper TTS error: {e}")
            return False

    async def stop(self) -> None:
        pass


class PiperCLITTS:
    """TTS using the `piper` CLI binary (requires piper installed via pip/apt)."""

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


class MockTTS:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def speak(self, text: str) -> bool:
        logger.info(f"[MOCK TTS] {text}")
        return True

    async def stop(self) -> None:
        pass


def create_tts(settings: Settings):
    """Factory — tries engines in order of offline capability."""
    engine = settings.voice.tts_engine

    if engine == "sarvam":
        return SarvamTTS(settings)

    if engine == "piper":
        # Try the Python package first (no CLI binary needed), then fall back to CLI
        try:
            from piper.voice import PiperVoice  # noqa: F401
            return PiperTTS(settings)
        except ImportError:
            logger.warning("piper-tts Python package not installed, trying CLI...")
            try:
                import shutil
                if shutil.which("piper"):
                    return PiperCLITTS(settings)
            except Exception:
                pass
            logger.warning("Piper (both Python package and CLI) not available, using mock TTS")
            return MockTTS(settings)

    # Default: auto-detect best offline option
    try:
        from piper.voice import PiperVoice  # noqa: F401
        return PiperTTS(settings)
    except ImportError:
        pass

    try:
        import shutil
        if shutil.which("piper"):
            return PiperCLITTS(settings)
    except Exception:
        pass

    logger.warning("No offline TTS engine available (install piper-tts), using mock TTS")
    return MockTTS(settings)
