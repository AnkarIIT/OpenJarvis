import pytest

from jarvis.config.settings import Settings
from jarvis.voice.pipeline import VoicePipeline


class FakeWakeWord:
    def __init__(self):
        self.started = 0
        self.stopped = 0

    async def start(self):
        self.started += 1
        return True

    async def stop(self):
        self.stopped += 1


class FakeTTS:
    def __init__(self):
        self.spoken = []

    async def speak(self, text):
        self.spoken.append(text)
        return True

    async def stop(self):
        pass


class FakeSTT:
    async def listen_once(self, timeout=10.0):
        return ""


@pytest.mark.asyncio
async def test_wake_word_greets_and_rearms_listener(monkeypatch):
    monkeypatch.setattr("jarvis.voice.pipeline.create_tts", lambda settings: FakeTTS())
    monkeypatch.setattr("jarvis.voice.pipeline.create_stt", lambda settings: FakeSTT())
    monkeypatch.setattr(
        "jarvis.voice.pipeline.create_wake_word",
        lambda settings, callback: FakeWakeWord(),
    )

    pipeline = VoicePipeline(Settings(), object())
    await pipeline._on_wake_word()

    assert pipeline.tts.spoken == ["Hello Master"]
    assert pipeline.wake_word.stopped == 1
    assert pipeline.wake_word.started == 1
    assert pipeline._handling_wake_word is False
