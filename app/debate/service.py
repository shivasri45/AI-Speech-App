"""Debate turn analysis service.

Inlines the same pipeline used by ``POST /analyze`` (``analyze_audio`` in
``app.api.analysis_routes``) but adapted for a debate turn:

- No ``expected_text`` is supplied — debate turns are free-form speech.
- The ``communication`` section is marked N/A for debate turns.
- The ``debug`` section is a stub (no transcript comparison).
- ``save_attempt`` failures are swallowed at WARNING so a persistence
  hiccup never blocks a turn from being recorded upstream.

Public callables:

- ``analyze_turn_audio(file, user)``: runs the full pipeline and returns
  ``(audio_asset, transcription, pronunciation, fluency, analysis_id)``
  for the room manager to combine with participant/turn metadata.
- ``compute_ai_score(pronunciation, fluency)``: pure function that folds
  the two per-turn signals into a single 0–100 score, returning also a
  boolean flag when neither signal was usable.
"""

from uuid import uuid4

from fastapi import UploadFile

from app.asr.schemas import TranscriptionResult
from app.asr.whisper_service import transcribe_audio
from app.attempts.schemas import build_attempt_summary
from app.attempts.storage import save_attempt
from app.audio.preprocessing import preprocess_audio_asset
from app.audio.schemas import AudioAsset
from app.audio.storage import save_uploaded_audio
from app.auth import User
from app.core.logging_helpers import logger
from app.core.logging_helpers import stage_log
from app.fluency.schemas import FluencyResult
from app.fluency.service import build_fluency_section
from app.pronunciation.service import assess_pronunciation
from app.schemas.pronunciation_schema import AnalyzeResponse
from app.schemas.pronunciation_schema import PronunciationResult


async def analyze_turn_audio(
    file: UploadFile,
    user: User,
) -> tuple[AudioAsset, TranscriptionResult, PronunciationResult, FluencyResult, str]:
    """Run the full analysis pipeline for a single debate turn.

    Mirrors ``app.api.analysis_routes.analyze_audio`` step-for-step, minus
    the transcript-comparison branch (no ``expected_text`` for debate) and
    with a debate-specific ``communication`` stub. Persistence via
    ``save_attempt`` is best-effort; failures are logged and swallowed.

    Args:
        file: The uploaded audio blob from the turn upload endpoint.
        user: The authenticated caller (kept for parity with the analyze
            route; not used inside the pipeline itself).

    Returns:
        A 5-tuple ``(audio_asset, transcription, pronunciation, fluency,
        analysis_id)`` for the room manager to persist as a ``DebateTurn``.
    """
    analysis_id = str(uuid4())

    logger.info(
        stage_log(
            "debate_turn_received",
            analysis_id,
            content_type=file.content_type,
            size_hint=getattr(file, "size", None) or "unknown",
        )
    )

    audio_asset = await save_uploaded_audio(file)
    logger.info(
        stage_log(
            "audio_saved",
            analysis_id,
            audio_id=audio_asset.audio_id,
            size_bytes=audio_asset.size_bytes,
        )
    )

    audio_asset = preprocess_audio_asset(audio_asset)
    logger.info(
        stage_log(
            "audio_preprocessed",
            analysis_id,
            audio_id=audio_asset.audio_id,
            duration=audio_asset.duration_seconds,
        )
    )

    transcription = transcribe_audio(audio_asset.processed_path)
    logger.info(
        stage_log(
            "asr_done",
            analysis_id,
            provider=transcription.provider,
            word_count=len(transcription.words),
        )
    )

    # Enable pronunciation assessment using transcribed text as reference.
    # HF phoneme model can assess acoustic quality even without pre-defined
    # expected text by using the ASR transcript as the expected baseline.
    expected_text_for_pronunciation = transcription.text if transcription.text else None
    
    pronunciation = assess_pronunciation(
        audio_path=audio_asset.processed_path,
        expected_text=expected_text_for_pronunciation,
        transcription=transcription,
        analysis_id=analysis_id,
    )
    logger.info(
        stage_log(
            "pronunciation_done",
            analysis_id,
            available=pronunciation.available,
            overall_score=pronunciation.overall_score,
        )
    )

    fluency = build_fluency_section(
        transcription=transcription,
        audio_asset=audio_asset,
    )
    logger.info(
        stage_log(
            "fluency_done",
            analysis_id,
            wpm=fluency.words_per_minute,
            clarity=fluency.clarity_score,
        )
    )

    response = AnalyzeResponse(
        analysis_id=analysis_id,
        audio=audio_asset,
        transcription=transcription,
        pronunciation=pronunciation,
        fluency=fluency,
        communication={
            "available": False,
            "provider": None,
            "overall_score": None,
            "rubric_version": None,
            "message": "N/A for debate turns",
        },
        debug={
            "expected_text_provided": False,
            "expected_text": None,
            "transcript_match_score": None,
            "transcript_mistakes": [],
        },
    )

    try:
        save_attempt(
            build_attempt_summary(
                analysis_id=analysis_id,
                response_data=response.model_dump(),
            )
        )
    except Exception as exc:
        logger.warning(
            stage_log(
                "attempt_persist_failed",
                analysis_id,
                exc=type(exc).__name__,
            )
        )

    return audio_asset, transcription, pronunciation, fluency, analysis_id


def compute_ai_score(
    pronunciation: PronunciationResult,
    fluency: FluencyResult,
) -> tuple[float, bool]:
    """Fold pronunciation and fluency signals into a single 0–100 score.

    Priority (per design section "AI Score Computation"):

    1. Both pronunciation (available) and fluency clarity present →
       average of the two, clamped to ``[0, 100]``, rounded to 2 decimals.
       ``scoring_unavailable`` is ``False``.
    2. Only fluency clarity present → clarity value, clamped and rounded.
       ``scoring_unavailable`` is ``False``.
    3. Neither present → ``(0.0, True)`` so upstream can flag the turn as
       lacking scoreable content while still persisting a numeric score.

    Args:
        pronunciation: Result from ``assess_pronunciation``. May be
            ``None`` or have ``available=False``; both are treated as
            "pronunciation missing".
        fluency: Result from ``build_fluency_section``. ``clarity_score``
            may be ``None``.

    Returns:
        A tuple ``(ai_score, scoring_unavailable)``.
    """
    pron = (
        pronunciation.overall_score
        if pronunciation is not None and pronunciation.available
        else None
    )
    clarity = fluency.clarity_score if fluency is not None else None
    if pron is not None and clarity is not None:
        return (
            round(max(0.0, min(100.0, (float(pron) + float(clarity)) / 2.0)), 2),
            False,
        )
    if clarity is not None:
        return round(max(0.0, min(100.0, float(clarity))), 2), False
    return 0.0, True
