from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Optional

from jarvis.config.settings import Settings
from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class VoiceControlSkill:
    name: str = "voice_control"
    description: str = "Voice interaction control: enable/disable listening, test TTS"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings
        self._voice_pipeline = None

    async def initialize(self, settings: Settings) -> None:
        self.settings = settings

    def set_voice_pipeline(self, pipeline: Any) -> None:
        """Allow the app to inject the active VoicePipeline instance."""
        self._voice_pipeline = pipeline

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="voice_on",
                description="Enable voice listening and wake word detection",
                handler=self._voice_on,
                skill_name=self.name,
            ),
            SkillCommand(
                name="voice_off",
                description="Disable voice listening and mute TTS output",
                handler=self._voice_off,
                skill_name=self.name,
            ),
            SkillCommand(
                name="voice_test",
                description="Test voice output by speaking the provided text",
                handler=self._voice_test,
                skill_name=self.name,
            ),
            SkillCommand(
                name="language",
                description="Set the language JARVIS responds in (BCP-47 code, e.g. en-IN, hi-IN, ta-IN). Use 'auto' for auto-detection.",
                handler=self._set_language,
                skill_name=self.name,
            ),
        ]

    async def _voice_on(self) -> str:
        if not self.settings:
            return "Voice settings not available."

        self.settings.voice.enabled = True
        if self._voice_pipeline is not None:
            try:
                if not self._voice_pipeline.is_listening:
                    await self._voice_pipeline.start_listening()
                return "Voice listening enabled via pipeline."
            except Exception as e:
                logger.error(f"Failed to start voice pipeline: {e}")
                return f"Voice enabled in settings, but pipeline start failed: {e}"
        return "Voice enabled in settings. Restart may be required for wake-word listener."

    async def _voice_off(self) -> str:
        if not self.settings:
            return "Voice settings not available."

        self.settings.voice.enabled = False
        if self._voice_pipeline is not None:
            try:
                if self._voice_pipeline.is_listening:
                    await self._voice_pipeline.stop_listening()
                return "Voice listening disabled via pipeline."
            except Exception as e:
                logger.error(f"Failed to stop voice pipeline: {e}")
                return f"Voice disabled in settings, but pipeline stop failed: {e}"
        return "Voice disabled in settings."

    async def _voice_test(self, text: str = "Voice systems operational, Sir.") -> str:
        if self._voice_pipeline is not None:
            try:
                ok = await self._voice_pipeline.speak(text)
                if ok:
                    return f"Spoke via pipeline: {text}"
                return "Pipeline TTS returned false."
            except Exception as e:
                logger.error(f"Pipeline TTS failed: {e}")

        # Fallback: create a temporary TTS instance
        try:
            from jarvis.voice.tts import create_tts
            tts = create_tts(self.settings)
            ok = await tts.speak(text)
            return f"Spoke via TTS: {text}" if ok else "TTS failed."
        except Exception as e:
            logger.error(f"TTS test failed: {e}")
            return f"Voice test failed: {e}"

    async def _set_language(self, language_code: str = "en-IN") -> str:
        if not self.settings:
            return "Language settings not available."

        # Map "auto" to unknown for auto-detection
        if language_code.lower() == "auto":
            language_code = "unknown"
            self.settings.voice.language_detection = True
        else:
            self.settings.voice.language = language_code
            self.settings.voice.language_detection = False

        if self._voice_pipeline is not None and hasattr(self._voice_pipeline, "set_language"):
            self._voice_pipeline.set_language(language_code)

        if language_code == "unknown":
            return "Language set to auto-detect. JARVIS will respond in the detected language."
        return f"Language set to: {language_code}. JARVIS will respond in this language."
