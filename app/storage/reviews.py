"""Teacher reviews of interview submissions.

One review row per teacher review. The submission gets a cached summary
(`teacher_score`, `combined_score`) for fast list rendering, but the
full rubric breakdown lives here.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel
from pydantic import Field

from ._jsonl import append_jsonl
from ._jsonl import read_jsonl


class RubricScore(BaseModel):
    structure: int = 0  # 0..10
    clarity: int = 0
    evidence: int = 0
    presence: int = 0


class InterviewReview(BaseModel):
    review_id: str = Field(default_factory=lambda: str(uuid4()))
    submission_id: str
    reviewer_email: str
    reviewer_uid: str
    reviewer_name: Optional[str] = None
    rubric: RubricScore = Field(default_factory=RubricScore)
    comment: str = ""
    # 0..100, derived from rubric average × 10. Stored for fast reads.
    teacher_score: int = 0
    # 0..100, weighted combination of gesture + teacher. Stored for fast reads.
    combined_score: int = 0
    reviewed_at: str


_PATH = Path("outputs/interview_reviews.jsonl")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_teacher_score(rubric: RubricScore) -> int:
    """Map a rubric (0..10 per criterion) to a 0..100 overall."""
    parts = [rubric.structure, rubric.clarity, rubric.evidence, rubric.presence]
    avg = sum(parts) / len(parts)
    return max(0, min(100, round(avg * 10)))


def compute_combined_score(gesture_score: int, teacher_score: int) -> int:
    """50/50 weighting between the AI body-language score and the teacher
    rubric score. Adjust here if weights need tuning later."""
    combined = 0.5 * gesture_score + 0.5 * teacher_score
    return max(0, min(100, round(combined)))


class ReviewsStore:
    path: Path

    def __init__(self, path: Path = _PATH):
        self.path = path

    def list_all(self) -> list[InterviewReview]:
        raw = read_jsonl(self.path)
        out: list[InterviewReview] = []
        for row in raw:
            try:
                out.append(InterviewReview(**row))
            except Exception:
                continue
        return out

    def get_for_submission(self, submission_id: str) -> Optional[InterviewReview]:
        for review in self.list_all():
            if review.submission_id == submission_id:
                return review
        return None

    def list_by_reviewer(self, reviewer_email: str) -> list[InterviewReview]:
        normalized = reviewer_email.lower()
        return [r for r in self.list_all() if r.reviewer_email.lower() == normalized]

    def create(
        self,
        submission_id: str,
        reviewer_email: str,
        reviewer_uid: str,
        reviewer_name: Optional[str],
        rubric: RubricScore,
        comment: str,
        gesture_score: int,
    ) -> InterviewReview:
        teacher_score = compute_teacher_score(rubric)
        combined_score = compute_combined_score(gesture_score, teacher_score)
        record = InterviewReview(
            submission_id=submission_id,
            reviewer_email=reviewer_email.lower(),
            reviewer_uid=reviewer_uid,
            reviewer_name=reviewer_name,
            rubric=rubric,
            comment=comment,
            teacher_score=teacher_score,
            combined_score=combined_score,
            reviewed_at=_now(),
        )
        append_jsonl(self.path, record.model_dump())
        return record


reviews_store = ReviewsStore()
