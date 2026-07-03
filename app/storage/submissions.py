"""Interview Studio submission records.

A submission is created when a student clicks "Submit for teacher review"
after the ss3 gesture analysis finishes. It captures:
- the question the student answered
- the gesture scores returned by ss3
- the ss3 session id (so the teacher can fetch the video via the proxy)
- the student's email + name
- review status (pending | reviewed | abandoned)

Once a teacher reviews it, a paired record lands in `reviews.py`. The
admin panel joins the two for the review table.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Literal
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel
from pydantic import Field

from ._jsonl import append_jsonl
from ._jsonl import overwrite_jsonl
from ._jsonl import read_jsonl


SubmissionStatus = Literal["pending", "reviewed", "abandoned"]


class GestureMetricSnapshot(BaseModel):
    name: str
    score: Optional[int] = None
    flag: str = "ok"


class InterviewSubmission(BaseModel):
    submission_id: str = Field(default_factory=lambda: str(uuid4()))
    student_email: str
    student_uid: str
    student_name: Optional[str] = None
    question_id: str
    question_prompt: str
    question_category: str
    # ss3 session id, used to fetch the video later through the proxy.
    gesture_session_id: Optional[str] = None
    gesture_score: int = 0
    gesture_metrics: list[GestureMetricSnapshot] = Field(default_factory=list)
    duration_seconds: float = 0.0
    status: SubmissionStatus = "pending"
    submitted_at: str
    reviewed_at: Optional[str] = None
    # Cached review summary for fast list rendering — actual review record
    # lives in `reviews.jsonl`. Updated when a teacher submits a review.
    teacher_score: Optional[int] = None
    combined_score: Optional[int] = None


_PATH = Path("outputs/interview_submissions.jsonl")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SubmissionsStore:
    path: Path

    def __init__(self, path: Path = _PATH):
        self.path = path

    # --- Read ---

    def list_all(self) -> list[InterviewSubmission]:
        raw = read_jsonl(self.path)
        out: list[InterviewSubmission] = []
        for row in raw:
            try:
                out.append(InterviewSubmission(**row))
            except Exception:
                continue
        return out

    def list_pending(self) -> list[InterviewSubmission]:
        return [s for s in self.list_all() if s.status == "pending"]

    def list_for_student(self, email: str) -> list[InterviewSubmission]:
        normalized = email.lower()
        return [s for s in self.list_all() if s.student_email.lower() == normalized]

    def get(self, submission_id: str) -> Optional[InterviewSubmission]:
        for s in self.list_all():
            if s.submission_id == submission_id:
                return s
        return None

    # --- Write ---

    def create(
        self,
        student_email: str,
        student_uid: str,
        student_name: Optional[str],
        question_id: str,
        question_prompt: str,
        question_category: str,
        gesture_session_id: Optional[str],
        gesture_score: int,
        gesture_metrics: list[dict],
        duration_seconds: float,
    ) -> InterviewSubmission:
        record = InterviewSubmission(
            student_email=student_email.lower(),
            student_uid=student_uid,
            student_name=student_name,
            question_id=question_id,
            question_prompt=question_prompt,
            question_category=question_category,
            gesture_session_id=gesture_session_id,
            gesture_score=int(gesture_score or 0),
            gesture_metrics=[
                GestureMetricSnapshot(**m) if isinstance(m, dict) else m
                for m in gesture_metrics
            ],
            duration_seconds=float(duration_seconds or 0.0),
            status="pending",
            submitted_at=_now(),
        )
        append_jsonl(self.path, record.model_dump())
        return record

    def mark_reviewed(
        self,
        submission_id: str,
        teacher_score: int,
        combined_score: int,
    ) -> Optional[InterviewSubmission]:
        """Flip `status=reviewed` and stash the cached scores. Full rewrite
        because we're mutating an existing row."""
        rows = read_jsonl(self.path)
        updated: Optional[InterviewSubmission] = None
        out: list[dict] = []
        now = _now()
        for raw in rows:
            try:
                record = InterviewSubmission(**raw)
            except Exception:
                out.append(raw)  # preserve as-is
                continue
            if record.submission_id == submission_id:
                record = record.model_copy(
                    update={
                        "status": "reviewed",
                        "reviewed_at": now,
                        "teacher_score": int(teacher_score),
                        "combined_score": int(combined_score),
                    }
                )
                updated = record
            out.append(record.model_dump())
        if updated is not None:
            overwrite_jsonl(self.path, out)
        return updated


submissions_store = SubmissionsStore()
