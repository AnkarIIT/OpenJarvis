from __future__ import annotations

import asyncio
from typing import Optional

from jarvis.agent.loop import AgentLoop
from jarvis.config.settings import Settings
from jarvis.voice.tts import create_tts
from jarvis.voice.stt import create_stt
from jarvis.voice.wake_word import create_wake_word
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class VoicePipeline:
    def __init__(self, settings: Settings, agent_loop: AgentLoop):
        self.settings = settings
        self.agent_loop = agent_loop
        self.tts = create_tts(settings)
        self.stt = create_stt(settings)
        self.wake_word = create_wake_word(settings, self._on_wake_word)
        self.is_listening = False
        self.push_to_talk = False
        self._listen_task: Optional[asyncio.Task] = None

    async def start_wake_word_listener(self) -> None:
        if self.settings.voice.wake_word_enabled:
            await self.wake_word.start()

    async def stop_wake_word_listener(self) -> None:
        await self.wake_word.stop()

    async def _on_wake_word(self) -> None:
        if not self.is_listening:
            await self.start_listening()
            await self._process_voice_command()

    async def start_listening(self) -> None:
        if self.is_listening:
            return
        self.is_listening = True
        logger.info("Voice listening started")

    async def stop_listening(self) -> None:
        self.is_listening = False
        logger.info("Voice listening stopped")

    def toggle_listening(self) -> None:
        if self.is_listening:
            asyncio.create_task(self.stop_listening())
        else:
            asyncio.create_task(self.start_listening())

    async def _process_voice_command(self) -> None:
        text = await self.stt.listen_once(timeout=10.0)
        if text:
            logger.info(f"Voice command: {text}")
            async for chunk in self.agent_loop.run(text, voice_mode=True):
                pass
            await self.speak_last_response()

    async def speak_last_response(self) -> None:
        if self.agent_loop.conversation_history:
            last_msg = self.agent_loop.conversation_history[-1]
            if last_msg.get("role") == "assistant":
                await self.tts.speak(last_msg["content"])

    async def speak(self, text: str) -> bool:
        return await self.tts.speak(text)

    def set_language(self, language_code: str) -> None:
        """Set the response language for both TTS and STT."""
        self.settings.voice.language = language_code
        if hasattr(self.tts, "language_code"):
            self.tts.language_code = language_code
        logger.info(f"JARVIS language set to: {language_code}")

    async def listen_once(self) -> str:
        return await self.stt.listen_once()

    async def calibrate(self) -> None:
        logger.info("Calibrating microphone...")
        await asyncio.sleep(2)
        logger.info("Calibration complete")

    async def stop(self) -> None:
        await self.stop_wake_word_listener()
        await self.tts.stop()
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass