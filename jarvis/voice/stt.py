from __future__ import annotations

import asyncio
import json
import os
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

import sounddevice as sd
import numpy as np

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

# Pre-defined model URLs for auto-download
_VOSK_MODELS = {
    "small-en-us": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
    "small-hi": "https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip",
}


def _ensure_vosk_model(model_name: str) -> Path | None:
    """Auto-download Vosk model if not present."""
    config_dir = Path(os.path.expanduser("~/.jarvis/voice"))
    config_dir.mkdir(parents=True, exist_ok=True)

    model_path = config_dir / model_name
    if model_path.exists():
        return model_path

    zip_name = f"{model_name}.zip"
    zip_path = config_dir / zip_name

    if model_name in _VOSK_MODELS:
        url = _VOSK_MODELS[model_name]
        logger.info(f"Downloading Vosk model '{model_name}' from {url}...")
        try:
            urllib.request.urlretrieve(url, str(zip_path))
            logger.info(f"Downloaded {zip_name}")
        except Exception as e:
            logger.error(f"Failed to download Vosk model: {e}")
            return None
    else:
        logger.error(f"Unknown Vosk model: {model_name}. Available: {list(_VOSK_MODELS.keys())}")
        return None

    # Extract
    try:
        logger.info(f"Extracting {zip_name}...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(str(config_dir))
        # The extracted folder may have a different name
        extracted_dirs = [d for d in config_dir.iterdir() if d.is_dir() and d.name.startswith("vosk-model")]
        if extracted_dirs:
            # Rename to expected path
            extracted = extracted_dirs[0]
            if extracted != model_path:
                extracted.rename(model_path)
        return model_path
    except Exception as e:
        logger.error(f"Failed to extract Vosk model: {e}")
        return None


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
            if not self.model_path.exists():
                # Try auto-download
                logger.info(f"Vosk model not found at {self.model_path}, attempting auto-download...")
                downloaded = _ensure_vosk_model(self.settings.voice.stt_model)
                if downloaded:
                    self.model_path = downloaded
                else:
                    logger.warning(f"Vosk model not available: {self.model_path}")
                    return

            self.model = Model(str(self.model_path))
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            logger.info("Vosk STT model loaded")
        except ImportError:
            logger.warning("Vosk not installed — will use fallback STT")
        except Exception as e:
            logger.error(f"Vosk model init error: {e}")

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


class WhisperSTT:
    """STT using whisper.cpp via pywhispercpp — fully offline."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_name = "base.en"  # Default — small, good accuracy
        self.sample_rate = 16000
        self._model = None

    async def _ensure_model(self) -> bool:
        if self._model is not None:
            return True
        try:
            from pywhispercpp.model import Model
            # The model will auto-download on first use
            self._model = Model(self.model_name)
            logger.info(f"Whisper model loaded: {self.model_name}")
            return True
        except ImportError:
            logger.warning("pywhispercpp not installed — will use fallback STT")
            return False
        except Exception as e:
            logger.error(f"Whisper model load error: {e}")
            return False

    async def listen_once(self, timeout: float = 10.0) -> str:
        if not await self._ensure_model():
            return ""

        try:
            # Record audio using sounddevice
            audio_queue = asyncio.Queue()

            def callback(indata, frames, time, status):
                if status:
                    logger.warning(f"Audio callback status: {status}")
                pcm = bytes(indata)
                asyncio.run_coroutine_threadsafe(audio_queue.put(pcm), asyncio.get_event_loop())

            stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=4000,
                dtype='int16',
                channels=1,
                callback=callback,
            )

            logger.info("Recording (Whisper)...")
            audio_data = b""
            start_time = asyncio.get_event_loop().time()

            with stream:
                while asyncio.get_event_loop().time() - start_time < timeout:
                    try:
                        data = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                        audio_data += data
                        if len(audio_data) > 0:
                            # For simplicity, stop early if we have enough audio
                            if len(audio_data) > self.sample_rate * 16:  # 16 seconds max
                                break
                    except asyncio.TimeoutError:
                        continue

            if not audio_data:
                return ""

            # Convert bytes to numpy array for whisper
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

            # Transcribe
            segments = self._model.transcribe(audio_array)
            text_parts = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    text_parts.append(text)

            result = " ".join(text_parts).strip()
            if result:
                logger.info(f"Heard (Whisper): {result}")
            return result

        except Exception as e:
            logger.error(f"Whisper STT error: {e}")
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
        self.sample_rate = settings.voice.sample_rate

    async def listen_once(self, timeout: float = 10.0) -> str:
        if not self.api_key:
            logger.warning("Sarvam STT: API key not set")
            return ""

        import aiohttp

        try:
            # Record audio using sounddevice
            frames = []

            def callback(indata, frames_count, time, status):
                if status:
                    logger.warning(f"Audio callback status: {status}")
                frames.append(bytes(indata))

            stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                callback=callback,
            )

            try:
                with stream:
                    logger.info("Recording (Sarvam)...")
                    await asyncio.sleep(min(timeout, 10.0))
            except Exception:
                pass

            if not frames:
                return ""

            audio_bytes = b"".join(frames)

            url = "https://api.sarvam.ai/speech-to-text"
            headers = {"api-subscription-key": self.api_key}

            # Convert to WAV
            import wave
            import io as io_module
            buf = io_module.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_bytes)
            wav_data = buf.getvalue()

            form = aiohttp.FormData()
            form.add_field("file", wav_data, filename="audio.wav", content_type="audio/wav")
            form.add_field("model", self.model)
            if self.settings.voice.language_detection:
                form.add_field("language_code", "unknown")
            else:
                form.add_field("language_code", self.settings.voice.language)

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=form, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"Sarvam STT error: {resp.status} {await resp.text()}")
                        return ""
                    result = await resp.json()

            transcript = result.get("transcript", "").strip()
            detected_lang = result.get("language_code")
            if detected_lang and self.settings.voice.language_detection:
                self.settings.voice.language = detected_lang

            if transcript:
                logger.info(f"Heard (Sarvam): {transcript} (language: {detected_lang})")
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
    """Factory — tries engines in order of offline capability."""
    engine = settings.voice.stt_engine

    if engine == "sarvam":
        return SarvamSTT(settings)
    elif engine == "whisper":
        return WhisperSTT(settings)

    # Default: try Vosk (offline), then Whisper (offline), then mock
    try:
        from vosk import Model  # noqa: F401
        return VoskSTT(settings)
    except ImportError:
        pass

    try:
        from pywhispercpp import Model  # noqa: F401
        logger.info("Vosk not available, using Whisper.cpp (offline)")
        return WhisperSTT(settings)
    except ImportError:
        if engine == "vosk":
            logger.warning("Vosk not available, using mock STT")
        elif engine == "whisper":
            logger.warning("pywhispercpp not available, using mock STT")
        return MockSTT(settings)
