"""Content scoring for debate turns using LLM.

Evaluates the relevance, argument quality, structure, and vocabulary
of a speaker's transcript against the debate motion.

Scoring breakdown (50 points total):
- Relevance (0-15): Does it address the motion directly?
- Arguments (0-15): Are points logical and supported?
- Structure (0-10): Clear intro, body, conclusion?
- Vocabulary (0-10): Word variety, appropriate terms?
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.core.llm_client import llm

logger = logging.getLogger("debate.content_scoring")


@dataclass
class ContentScoreResult:
    """Result of content scoring analysis."""

    relevance: int  # 0-15
    arguments: int  # 0-15
    structure: int  # 0-10
    vocabulary: int  # 0-10
    total: int  # 0-50
    feedback: str  # One-line feedback
    available: bool  # Whether scoring succeeded
    error: Optional[str] = None  # Error message if failed

    def to_dict(self) -> dict:
        return {
            "relevance": self.relevance,
            "arguments": self.arguments,
            "structure": self.structure,
            "vocabulary": self.vocabulary,
            "total": self.total,
            "feedback": self.feedback,
            "available": self.available,
            "error": self.error,
        }


def _build_scoring_prompt(transcript: str, motion_title: str, motion_text: str) -> str:
    """Build the LLM prompt for content scoring."""
    return f"""You are a strict debate judge scoring a student's speech. Be fair but honest - students need real feedback to improve.

DEBATE MOTION: {motion_title}
"{motion_text}"

STUDENT'S SPEECH TRANSCRIPT:
"{transcript}"

Score the speech on these criteria:

1. RELEVANCE (0-15): Does it directly address the motion? 
   - 13-15: Fully on topic, strong connection to motion
   - 9-12: Mostly relevant, minor tangents
   - 5-8: Partially relevant, missing key aspects
   - 0-4: Off topic or barely addresses motion

2. ARGUMENTS (0-15): Are the points logical and supported?
   - 13-15: Clear reasoning, good examples/evidence
   - 9-12: Decent logic, some support
   - 5-8: Weak arguments, unsupported claims
   - 0-4: No clear arguments or illogical

3. STRUCTURE (0-10): Is there clear organization?
   - 8-10: Clear intro, body, conclusion
   - 5-7: Some structure but disorganized
   - 0-4: No clear structure, rambling

4. VOCABULARY (0-10): Word variety and appropriateness?
   - 8-10: Rich vocabulary, no repetition
   - 5-7: Adequate vocabulary
   - 0-4: Repetitive, limited words

Respond with ONLY valid JSON (no explanation, no markdown):
{{"relevance": <0-15>, "arguments": <0-15>, "structure": <0-10>, "vocabulary": <0-10>, "total": <0-50>, "feedback": "<one sentence feedback in simple English or Hinglish>"}}"""


def _create_unavailable_result(error: str) -> ContentScoreResult:
    """Create a result indicating scoring is unavailable."""
    return ContentScoreResult(
        relevance=0,
        arguments=0,
        structure=0,
        vocabulary=0,
        total=0,
        feedback=error,
        available=False,
        error=error,
    )


async def score_debate_content(
    transcript: str,
    motion_title: str,
    motion_text: str,
) -> ContentScoreResult:
    """Score the content relevance of a debate speech.

    Args:
        transcript: The speaker's transcribed speech
        motion_title: Title of the debate motion
        motion_text: Full text of the debate motion

    Returns:
        ContentScoreResult with breakdown scores and feedback
    """
    # Validate inputs
    if not transcript or len(transcript.strip()) < 20:
        return _create_unavailable_result("Transcript too short for content analysis")

    if not motion_title or not motion_text:
        return _create_unavailable_result("Motion information missing")

    if not llm.is_available:
        return _create_unavailable_result("LLM service not configured")

    try:
        prompt = _build_scoring_prompt(transcript.strip(), motion_title, motion_text)
        result = await llm.generate_json(prompt, max_tokens=300)

        if not result:
            return _create_unavailable_result("Could not parse LLM response")

        # Extract and validate scores
        relevance = max(0, min(15, int(result.get("relevance", 0))))
        arguments = max(0, min(15, int(result.get("arguments", 0))))
        structure = max(0, min(10, int(result.get("structure", 0))))
        vocabulary = max(0, min(10, int(result.get("vocabulary", 0))))
        total = relevance + arguments + structure + vocabulary
        feedback = str(result.get("feedback", ""))[:200]

        logger.info(
            f"Content scored: relevance={relevance}, arguments={arguments}, "
            f"structure={structure}, vocabulary={vocabulary}, total={total}"
        )

        return ContentScoreResult(
            relevance=relevance,
            arguments=arguments,
            structure=structure,
            vocabulary=vocabulary,
            total=total,
            feedback=feedback or "Score computed successfully",
            available=True,
        )

    except Exception as e:
        logger.warning(f"Content scoring failed: {type(e).__name__}: {e}")
        return _create_unavailable_result(f"Scoring error: {type(e).__name__}")
