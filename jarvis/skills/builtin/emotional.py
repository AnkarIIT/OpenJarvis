from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class EmotionalIntelligenceSkill:
    name: str = "emotional"
    description: str = "Emotional awareness: sentiment analysis, mood tracking, empathy responses."
    version: str = "1.0.0"
    author: str = "OpenJarvis"

    def __init__(self, settings=None):
        self.settings = settings
        self.mood_history: list[dict] = []
        self.sentiment_cache: dict[str, float] = {}

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="emo_sentiment",
                description="Analyze sentiment of text: positive, negative, neutral.",
                handler=self._sentiment,
                skill_name=self.name,
            ),
            SkillCommand(
                name="emo_mood",
                description="Check current mood and history.",
                handler=self._mood,
                skill_name=self.name,
            ),
            SkillCommand(
                name="emo_empathy",
                description="Generate an empathetic response to the user's input.",
                handler=self._empathy,
                skill_name=self.name,
            ),
            SkillCommand(
                name="emo_tone",
                description="Analyze the tone of text: formal, casual, angry, sad, happy.",
                handler=self._tone,
                skill_name=self.name,
            ),
            SkillCommand(
                name="emo_reset",
                description="Reset mood history.",
                handler=self._reset,
                skill_name=self.name,
            ),
        ]

    async def initialize(self, settings) -> None:
        self.settings = settings

    async def _sentiment(self, text: str = "") -> str:
        if not text:
            return "Error: Provide text to analyze"

        # Simple sentiment analysis using keyword matching
        # In production, use transformers pipeline or VADER
        positive_words = {"good", "great", "awesome", "happy", "love", "excellent", "wonderful", "amazing", "best", "beautiful"}
        negative_words = {"bad", "terrible", "sad", "hate", "awful", "worst", "angry", "horrible", "pain", "cry"}

        words = text.lower().split()
        pos_count = sum(1 for w in words if w.strip(".,!?") in positive_words)
        neg_count = sum(1 for w in words if w.strip(".,!?") in negative_words)
        total = max(pos_count + neg_count, 1)

        score = (pos_count - neg_count) / total

        if score > 0.3:
            sentiment = "Positive"
            emoji = "😊"
        elif score < -0.3:
            sentiment = "Negative"
            emoji = "😔"
        else:
            sentiment = "Neutral"
            emoji = "😐"

        # Cache the result
        self.sentiment_cache[text[:50]] = score
        self.mood_history.append({
            "text": text[:100],
            "sentiment": sentiment,
            "score": score,
            "timestamp": str(Path(".")),
        })

        return (
            f"Sentiment: {sentiment} {emoji}\n"
            f"Score: {score:+.2f} (positive: {pos_count}, negative: {neg_count})\n"
            f"Words analyzed: {len(words)}"
        )

    async def _mood(self) -> str:
        if not self.mood_history:
            return "No mood history yet. Try: emo_sentiment 'I feel happy today'"

        recent = self.mood_history[-10:]
        positive = sum(1 for m in recent if m["score"] > 0)
        negative = sum(1 for m in recent if m["score"] < 0)
        neutral = len(recent) - positive - negative

        lines = ["Mood History (last 10):"]
        lines.append(f"  Positive: {positive} | Neutral: {neutral} | Negative: {negative}")

        if recent:
            latest = recent[-1]
            score = latest["score"]
            if score > 0.3:
                status = "Good"
            elif score < -0.3:
                status = "Low"
            else:
                status = "Stable"
            lines.append(f"\nCurrent status: {status}")

            # Show trend
            if len(recent) >= 3:
                scores = [m["score"] for m in recent[-5:]]
                if scores[-1] > scores[0]:
                    lines.append("Trend: ↑ Improving")
                elif scores[-1] < scores[0]:
                    lines.append("Trend: ↓ Declining")
                else:
                    lines.append("Trend: → Stable")

        return "\n".join(lines)

    async def _empathy(self, text: str = "") -> str:
        if not text:
            return "Error: Provide text to respond empathetically"

        # Simple empathetic response generator
        sentiment_score = self._quick_sentiment(text)

        if sentiment_score > 0.3:
            return (
                "I can feel the positive energy! 🌟\n"
                "That's wonderful to hear. Let me build on this momentum.\n"
                "What's next on your mind?"
            )
        elif sentiment_score < -0.3:
            return (
                "I hear you, and that sounds tough. 💙\n"
                "It's okay to feel that way. Let's work through this together.\n"
                "What would help right now?"
            )
        else:
            return (
                "I see. 👍\n"
                "Thanks for sharing that. It's important to express how you feel.\n"
                "Let me know if there's anything I can assist with."
            )

    async def _tone(self, text: str = "") -> str:
        if not text:
            return "Error: Provide text"

        words = text.lower()

        # Tone detection heuristics
        formal_words = {"please", "thank you", "respectfully", "kindly", "regarding", "furthermore"}
        casual_words = {"hey", "yeah", "gonna", "wanna", "dunno", "cool", "awesome", "lol"}
        angry_words = {"angry", "furious", "f***", "damn", "hell", "crap", "stupid"}
        sad_words = {"sad", "depressed", "lonely", "miss", "cry", "heartbroken"}

        formal = sum(1 for w in formal_words if w in words)
        casual = sum(1 for w in casual_words if w in words)
        angry = sum(1 for w in angry_words if w in words)
        sad = sum(1 for w in sad_words if w in words)

        scores = {"Formal": formal, "Casual": casual, "Angry": angry, "Sad": sad}
        dominant = max(scores, key=scores.get)

        if scores[dominant] == 0:
            dominant = "Neutral"

        return (
            f"Tone Analysis: {dominant}\n"
            f"  Formal: {formal} | Casual: {casual} | Angry: {angry} | Sad: {sad}"
        )

    async def _reset(self) -> str:
        self.mood_history.clear()
        self.sentiment_cache.clear()
        return "Mood history and sentiment cache reset ✓"

    def _quick_sentiment(self, text: str) -> float:
        positive_words = {"good", "great", "awesome", "happy", "love", "excellent", "wonderful", "amazing"}
        negative_words = {"bad", "terrible", "sad", "hate", "awful", "worst", "angry", "horrible"}
        words = text.lower().split()
        pos = sum(1 for w in words if w.strip(".,!?") in positive_words)
        neg = sum(1 for w in words if w.strip(".,!?") in negative_words)
        total = max(pos + neg, 1)
        return (pos - neg) / total
