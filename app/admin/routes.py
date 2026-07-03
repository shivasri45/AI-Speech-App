"""Teacher-only admin routes.

Every endpoint depends on `require_teacher`, so 401 (no token) and 403
(non-teacher email) responses are returned for free without touching
the handler bodies.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from fastapi import status

from app.auth import User
from app.auth import require_teacher
from app.core.config import settings
from app.storage import InterviewReview
from app.storage import InterviewSubmission
from app.storage import reviews_store
from app.storage import submissions_store
from app.storage import users_store
from app.storage.reviews import RubricScore

from .schemas import AdminAnalyticsResponse
from .schemas import AdminMeResponse
from .schemas import AdminStudentDetail
from .schemas import AdminStudentSummary
from .schemas import LeaderboardEntry
from .schemas import LeaderboardResponse
from .schemas import PendingSubmissionsResponse
from .schemas import ReviewSubmissionRequest
from .schemas import StudentListResponse
from .schemas import SubmissionDetailResponse


logger = logging.getLogger("admin.routes")

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


@router.get("/me", response_model=AdminMeResponse)
async def me(current_user: User = Depends(require_teacher)) -> AdminMeResponse:
    """Confirm the caller is a teacher. Used by the frontend to gate the
    Admin Panel tile."""
    return AdminMeResponse(
        email=current_user.email,
        display_name=current_user.name,
        role=current_user.role,
    )


# ---------------------------------------------------------------------------
# Pending / submissions
# ---------------------------------------------------------------------------


@router.get("/submissions/pending", response_model=PendingSubmissionsResponse)
async def list_pending(
    current_user: User = Depends(require_teacher),
) -> PendingSubmissionsResponse:
    del current_user  # role already enforced
    submissions = submissions_store.list_pending()
    # Newest first — matches student expectation.
    submissions.sort(key=lambda s: s.submitted_at, reverse=True)
    return PendingSubmissionsResponse(
        submissions=submissions,
        total=len(submissions),
    )


@router.get("/submissions/{submission_id}", response_model=SubmissionDetailResponse)
async def get_submission(
    submission_id: str,
    current_user: User = Depends(require_teacher),
) -> SubmissionDetailResponse:
    del current_user
    submission = submissions_store.get(submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="submission_not_found",
        )
    existing_review = reviews_store.get_for_submission(submission_id)
    return SubmissionDetailResponse(
        submission=submission,
        review=existing_review,
    )


@router.get("/submissions/{submission_id}/video")
async def stream_submission_video(
    submission_id: str,
    current_user: User = Depends(require_teacher),
) -> Response:
    """Serve the recorded video for one submission.

    ss3 stores every recording on the same host under
    ``{CSA_DATA_DIR}/sessions/{gesture_session_id}/video.webm``. Since
    ss3 doesn't expose an HTTP video endpoint, we read the file directly
    from disk. Falls back to a 404 with a clear code so the frontend can
    show a friendly "video unavailable" placeholder for older submissions.
    """
    from pathlib import Path

    del current_user
    submission = submissions_store.get(submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="submission_not_found",
        )
    gesture_session_id = submission.gesture_session_id
    if not gesture_session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="video_not_available",
        )

    data_dir = Path(settings.CSA_DATA_DIR).expanduser().resolve()
    session_dir = data_dir / "sessions" / gesture_session_id
    # ss3 defaults to `video.webm` but be tolerant of alternate extensions
    # that browser MediaRecorder might emit (mp4 on Safari, ogg edge cases).
    candidates = [
        session_dir / "video.webm",
        session_dir / "video.mp4",
        session_dir / "video.ogg",
    ]
    video_path = next((p for p in candidates if p.is_file()), None)
    if video_path is None:
        logger.info(
            "video not found for submission=%s session=%s dir=%s",
            submission_id,
            gesture_session_id,
            session_dir,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="video_file_missing",
        )

    ext = video_path.suffix.lstrip(".").lower()
    content_type = (
        "video/mp4"
        if ext == "mp4"
        else "video/ogg"
        if ext == "ogg"
        else "video/webm"
    )
    return Response(content=video_path.read_bytes(), media_type=content_type)


@router.post(
    "/submissions/{submission_id}/review",
    response_model=InterviewReview,
)
async def submit_review(
    submission_id: str,
    body: ReviewSubmissionRequest,
    current_user: User = Depends(require_teacher),
) -> InterviewReview:
    submission = submissions_store.get(submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="submission_not_found",
        )
    if submission.status == "reviewed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="already_reviewed",
        )

    rubric = RubricScore(
        structure=body.structure,
        clarity=body.clarity,
        evidence=body.evidence,
        presence=body.presence,
    )
    review = reviews_store.create(
        submission_id=submission_id,
        reviewer_email=current_user.email,
        reviewer_uid=current_user.uid,
        reviewer_name=current_user.name,
        rubric=rubric,
        comment=body.comment or "",
        gesture_score=submission.gesture_score,
    )
    submissions_store.mark_reviewed(
        submission_id=submission_id,
        teacher_score=review.teacher_score,
        combined_score=review.combined_score,
    )
    return review


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------


@router.get("/students", response_model=StudentListResponse)
async def list_students(
    current_user: User = Depends(require_teacher),
) -> StudentListResponse:
    del current_user
    student_users = users_store.list_by_role("student")
    summaries: list[AdminStudentSummary] = []
    all_submissions = submissions_store.list_all()
    submissions_by_email: dict[str, list[InterviewSubmission]] = {}
    for s in all_submissions:
        submissions_by_email.setdefault(s.student_email.lower(), []).append(s)

    for user in student_users:
        subs = submissions_by_email.get(user.email.lower(), [])
        reviewed = [s for s in subs if s.status == "reviewed" and s.combined_score is not None]
        avg_combined = (
            round(sum(s.combined_score or 0 for s in reviewed) / len(reviewed))
            if reviewed
            else None
        )
        summaries.append(
            AdminStudentSummary(
                email=user.email,
                display_name=user.display_name,
                first_seen_at=user.first_seen_at,
                last_seen_at=user.last_seen_at,
                submissions_total=len(subs),
                submissions_reviewed=len(reviewed),
                avg_combined_score=avg_combined,
            )
        )

    # Most active first.
    summaries.sort(key=lambda s: (s.submissions_total, s.last_seen_at), reverse=True)
    return StudentListResponse(students=summaries, total=len(summaries))


@router.get("/students/{email}", response_model=AdminStudentDetail)
async def get_student(
    email: str,
    current_user: User = Depends(require_teacher),
) -> AdminStudentDetail:
    del current_user
    user = users_store.get_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="student_not_found",
        )
    subs = submissions_store.list_for_student(email)
    subs.sort(key=lambda s: s.submitted_at, reverse=True)
    return AdminStudentDetail(
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        first_seen_at=user.first_seen_at,
        last_seen_at=user.last_seen_at,
        submissions=subs,
    )


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def analytics(
    current_user: User = Depends(require_teacher),
) -> AdminAnalyticsResponse:
    del current_user
    students = users_store.list_by_role("student")
    submissions = submissions_store.list_all()
    reviewed = [s for s in submissions if s.status == "reviewed" and s.combined_score is not None]
    pending_count = sum(1 for s in submissions if s.status == "pending")

    avg_gesture = (
        round(sum(s.gesture_score for s in submissions) / len(submissions))
        if submissions
        else None
    )
    avg_teacher = (
        round(sum(s.teacher_score for s in reviewed if s.teacher_score is not None) / len(reviewed))
        if reviewed
        else None
    )
    avg_combined = (
        round(sum(s.combined_score for s in reviewed if s.combined_score is not None) / len(reviewed))
        if reviewed
        else None
    )

    return AdminAnalyticsResponse(
        student_count=len(students),
        teacher_count=len(users_store.list_by_role("teacher")),
        submissions_total=len(submissions),
        submissions_pending=pending_count,
        submissions_reviewed=len(reviewed),
        avg_gesture_score=avg_gesture,
        avg_teacher_score=avg_teacher,
        avg_combined_score=avg_combined,
    )


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def leaderboard(
    limit: int = 10,
    current_user: User = Depends(require_teacher),
) -> LeaderboardResponse:
    del current_user
    cap = max(1, min(limit, 100))
    submissions = [
        s
        for s in submissions_store.list_all()
        if s.status == "reviewed" and s.combined_score is not None
    ]
    by_student: dict[str, list[InterviewSubmission]] = {}
    for s in submissions:
        by_student.setdefault(s.student_email.lower(), []).append(s)

    entries: list[LeaderboardEntry] = []
    for email, subs in by_student.items():
        best = max(subs, key=lambda s: s.combined_score or 0)
        avg = round(sum(s.combined_score or 0 for s in subs) / len(subs))
        record = users_store.get_by_email(email)
        entries.append(
            LeaderboardEntry(
                email=email,
                display_name=record.display_name if record else None,
                attempts=len(subs),
                best_score=best.combined_score or 0,
                avg_score=avg,
            )
        )
    entries.sort(key=lambda e: (e.best_score, e.avg_score, e.attempts), reverse=True)
    return LeaderboardResponse(entries=entries[:cap], total=len(entries))


def _exists_dummy_to_silence_unused_imports() -> Optional[str]:
    """Keep the optional import alive (used in handlers above)."""
    return None
