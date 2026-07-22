"""Tests for debate AI scoring rescale behavior.

Debate turns skip the (slow) HF phoneme pronunciation model, so the final
score must rescale from whatever signals ARE present (fluency + content)
back onto a 0-100 scale. These tests lock that behavior in.
"""

import asyncio
from unittest.mock import patch

from app.debate.service import compute_ai_score_with_content
from app.fluency.schemas import FluencyResult
from app.schemas.pronunciation_schema import PronunciationResult


def _skipped_pron():
    return PronunciationResult(
        available=False,
        provider="skipped_for_debate",
        overall_score=None,
        words=[],
        phoneme_errors=[],
    )


def _fluency(clarity):
    return FluencyResult(
        words_per_minute=140,
        clarity_score=clarity,
        speech_duration_seconds=60,
        total_duration_seconds=60,
    )


class _FakeContent:
    def __init__(self, total):
        self.available = True
        self.total = total
        self.feedback = "good"

    def to_dict(self):
        return {"total": self.total}


def test_debate_score_rescales_without_pronunciation():
    """fluency(25) + content(42) earned=67 of max 75 -> 89.33 rescaled."""

    async def scenario():
        with patch(
            "app.debate.service.score_debate_content",
            return_value=_FakeContent(42),
        ):
            score, unavailable, breakdown = await compute_ai_score_with_content(
                pronunciation=_skipped_pron(),
                fluency=_fluency(100),  # clarity 100 -> fluency_score 25
                transcript="a" * 100,   # long enough to trigger content scoring
                motion_title="M",
                motion_text="motion text here",
            )
        assert not unavailable
        # earned = 25 (fluency) + 42 (content) = 67; max = 25 + 50 = 75
        assert score == round(67 / 75 * 100, 2)
        assert breakdown["pronunciation"]["raw"] is None

    asyncio.run(scenario())


def test_debate_score_full_when_all_signals_high():
    """All present: fluency(25) + content(50) -> earned 75 of max 75 -> 100."""

    async def scenario():
        with patch(
            "app.debate.service.score_debate_content",
            return_value=_FakeContent(50),
        ):
            score, unavailable, _ = await compute_ai_score_with_content(
                pronunciation=_skipped_pron(),
                fluency=_fluency(100),
                transcript="a" * 100,
                motion_title="M",
                motion_text="motion text here",
            )
        assert not unavailable
        assert score == 100.0

    asyncio.run(scenario())


def test_debate_short_transcript_scores_on_fluency_only():
    """Transcript too short for content -> only fluency counts (rescaled)."""

    async def scenario():
        score, unavailable, breakdown = await compute_ai_score_with_content(
            pronunciation=_skipped_pron(),
            fluency=_fluency(80),  # clarity 80 -> fluency_score 20 of 25
            transcript="hi",       # too short for content scoring
            motion_title="M",
            motion_text="motion text",
        )
        # Only fluency present: earned 20, max 25 -> 80.0
        assert not unavailable
        assert score == 80.0
        assert breakdown["content"]["total"] is None

    asyncio.run(scenario())
