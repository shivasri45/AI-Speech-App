"""HTTP routes for Interview Studio.

`POST /interview/analyze` accepts a video upload, forwards it to the
ss3 gesture-analysis microservice, and returns a flattened response
the React `InterviewStudioView` can consume directly.

`POST /interview/submissions` then takes the gesture-analysis result
and persists a submission record awaiting teacher review.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import status
from pydantic import BaseModel
from pydantic import Field

from app.auth import User
from app.auth import require_user
from app.storage import submissions as submissions_store

from app.storage import reviews_store
from app.storage import submissions_store

from .schemas import InterviewAnalysisResponse
from .schemas import MySubmissionDetail
from .schemas import MySubmissionsResponse
from .schemas import InterviewSubmitRequest
from .schemas import InterviewSubmitResponse
from .service import CSAServiceError
from .service import analyze_video


logger = logging.getLogger("interview.routes")

router = APIRouter(prefix="/interview", tags=["interview"])


_MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB — webm @ 720p easily fits


class SubmitForReviewRequest(BaseModel):
    """Payload from the student after they've seen their gesture scores
    and want a teacher to grade the content too."""

    question_id: str
    question_prompt: str
    question_category: str = "general"
    gesture_session_id: str | None = None
    gesture_score: int = 0
    gesture_metrics: list[dict] = Field(default_factory=list)
    duration_seconds: float = 0.0


class SubmitForReviewResponse(BaseModel):
    submission_id: str
    status: str


@router.post("/analyze", response_model=InterviewAnalysisResponse)
async def analyze(
    video: UploadFile = File(...),
    current_user: User = Depends(require_user),
) -> InterviewAnalysisResponse:
    """Run gesture analysis on the uploaded interview video."""
    content_type = video.content_type or "video/webm"
    if not content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type: {content_type}",
        )

    payload = await video.read()
    if len(payload) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Video too large (max 100 MB).",
        )

    logger.info(
        "interview_analyze user=%s filename=%s size=%d",
        current_user.email,
        video.filename or "<unnamed>",
        len(payload),
    )

    try:
        result = await analyze_video(
            filename=video.filename or "recording.webm",
            content_type=content_type,
            video_bytes=payload,
        )
    except CSAServiceError as exc:
        logger.warning("csa_proxy_error %s", exc)
        # 502 — upstream service problem, not the user's fault.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    return result


@router.post("/submissions", response_model=InterviewSubmitResponse)
async def submit_for_review(
    body: InterviewSubmitRequest,
    current_user: User = Depends(require_user),
) -> InterviewSubmitResponse:
    """Persist a completed interview attempt for teacher review.

    The frontend calls this after `/interview/analyze` finishes — passing
    the gesture session id + scores so the submission can be reviewed
    later without re-running the analysis.
    """
    submission = submissions_store.create(
        student_email=current_user.email,
        student_uid=current_user.uid,
        student_name=current_user.name,
        question_id=body.question_id,
        question_prompt=body.question_prompt,
        question_category=body.question_category,
        gesture_session_id=body.gesture_session_id,
        gesture_score=body.gesture_score,
        gesture_metrics=[m.model_dump() for m in body.gesture_metrics],
        duration_seconds=body.duration_seconds,
    )
    logger.info(
        "interview_submission user=%s submission=%s",
        current_user.email,
        submission.submission_id,
    )
    return InterviewSubmitResponse(submission_id=submission.submission_id)


@router.get("/my-submissions", response_model=MySubmissionsResponse)
async def my_submissions(
    current_user: User = Depends(require_user),
) -> MySubmissionsResponse:
    """Every submission the current student has made, newest first.

    Used by Interview Studio's "My Submissions" panel so a student can
    check whether their pending submission has been reviewed yet.
    """
    subs = submissions_store.list_for_student(current_user.email)
    subs.sort(key=lambda s: s.submitted_at, reverse=True)
    return MySubmissionsResponse(submissions=subs, total=len(subs))


@router.get("/my-submissions/{submission_id}", response_model=MySubmissionDetail)
async def my_submission_detail(
    submission_id: str,
    current_user: User = Depends(require_user),
) -> MySubmissionDetail:
    """Full detail for one of the current student's submissions.

    Includes the teacher review (rubric + comment + combined score) once
    a teacher has posted it. Returns 403 if the submission belongs to
    someone else — students can only see their own work.
    """
    submission = submissions_store.get(submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="submission_not_found",
        )
    if submission.student_email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not_your_submission",
        )
    review = reviews_store.get_for_submission(submission_id)
    return MySubmissionDetail(submission=submission, review=review)


@router.post("/submissions", response_model=SubmitForReviewResponse)
async def submit_for_review(
    body: SubmitForReviewRequest,
    current_user: User = Depends(require_user),
) -> SubmitForReviewResponse:
    """Persist the student's interview attempt for teacher review.

    Called from the frontend after the AI gesture-analysis stage. The
    teacher's queue (`/admin/submissions/pending`) picks it up next.
    """
    submission = submissions_store.create(
        student_email=current_user.email,
        student_uid=current_user.uid,
        student_name=current_user.name or "",
        question_id=body.question_id,
        question_prompt=body.question_prompt,
        question_category=body.question_category,
        gesture_session_id=body.gesture_session_id,
        gesture_score=int(body.gesture_score or 0),
        gesture_metrics=body.gesture_metrics,
        duration_seconds=float(body.duration_seconds or 0.0),
    )
    logger.info(
        "interview_submission created id=%s student=%s",
        submission.submission_id,
        current_user.email,
    )
    return SubmitForReviewResponse(
        submission_id=submission.submission_id,
        status=submission.status,
    )


# ---------------------------------------------------------------------------
# Answer Content Scoring (Groq LLM)
# ---------------------------------------------------------------------------


class AnswerScoreRequest(BaseModel):
    """Request to score the content of a spoken answer."""
    question_prompt: str
    question_category: str = "general"


class AnswerScoreResponse(BaseModel):
    """AI content score for an interview answer."""
    relevance: int = 0
    structure: int = 0
    depth: int = 0
    communication: int = 0
    total: int = 0
    feedback: str = ""
    strengths: str = ""
    improvements: str = ""
    available: bool = False
    error: str | None = None
    transcript: str = ""


@router.post("/score-answer", response_model=AnswerScoreResponse)
async def score_answer(
    audio: UploadFile = File(...),
    question_prompt: str = "",
    question_category: str = "general",
    current_user: User = Depends(require_user),
) -> AnswerScoreResponse:
    """Score the content quality of a spoken interview answer.
    
    Accepts audio, transcribes it with Groq Whisper, then evaluates
    the answer quality using Groq LLM.
    
    This is complementary to /interview/analyze (which scores body language).
    Together they give a complete picture:
    - /interview/analyze → gesture_score (body language)
    - /interview/score-answer → content_score (what you said)
    """
    from app.asr.whisper_service import transcribe_audio
    from app.audio.preprocessing import preprocess_audio_asset
    from app.audio.storage import save_uploaded_audio
    from app.interview.content_scoring import score_interview_answer
    
    logger.info(
        "interview_score_answer user=%s question=%s",
        current_user.email,
        question_prompt[:50],
    )
    
    # Step 1: Save and preprocess audio
    try:
        audio_asset = await save_uploaded_audio(audio)
        audio_asset = preprocess_audio_asset(audio_asset)
    except Exception as exc:
        logger.warning(f"Audio processing failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process audio file.",
        )
    
    # Step 2: Transcribe with Groq Whisper (fast)
    try:
        transcription = transcribe_audio(str(audio_asset.processed_path))
        transcript = transcription.text or transcription.normalized_text or ""
    except Exception as exc:
        logger.warning(f"Transcription failed: {exc}")
        return AnswerScoreResponse(
            error="Transcription failed",
            feedback="Could not transcribe your answer. Please try again.",
        )
    
    if not transcript or len(transcript.strip()) < 20:
        return AnswerScoreResponse(
            transcript=transcript,
            feedback="Your answer was too short or unclear. Try speaking louder and longer (30+ seconds).",
            error="transcript_too_short",
        )
    
    # Step 3: Score content with LLM
    result = await score_interview_answer(
        transcript=transcript,
        question_prompt=question_prompt,
        question_category=question_category,
    )
    
    return AnswerScoreResponse(
        relevance=result.relevance,
        structure=result.structure,
        depth=result.depth,
        communication=result.communication,
        total=result.total,
        feedback=result.feedback,
        strengths=result.strengths,
        improvements=result.improvements,
        available=result.available,
        error=result.error,
        transcript=transcript,
    )
