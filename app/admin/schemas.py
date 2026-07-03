"""Pydantic shapes for the admin panel API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import conint

from app.storage import InterviewReview
from app.storage import InterviewSubmission


class AdminMeResponse(BaseModel):
    email: str
    display_name: Optional[str] = None
    role: str


class PendingSubmissionsResponse(BaseModel):
    submissions: list[InterviewSubmission] = Field(default_factory=list)
    total: int = 0


class SubmissionDetailResponse(BaseModel):
    submission: InterviewSubmission
    review: Optional[InterviewReview] = None


class ReviewSubmissionRequest(BaseModel):
    structure: conint(ge=0, le=10)  # type: ignore[valid-type]
    clarity: conint(ge=0, le=10)  # type: ignore[valid-type]
    evidence: conint(ge=0, le=10)  # type: ignore[valid-type]
    presence: conint(ge=0, le=10)  # type: ignore[valid-type]
    comment: str = ""


class AdminStudentSummary(BaseModel):
    email: str
    display_name: Optional[str] = None
    first_seen_at: str
    last_seen_at: str
    submissions_total: int = 0
    submissions_reviewed: int = 0
    avg_combined_score: Optional[int] = None


class StudentListResponse(BaseModel):
    students: list[AdminStudentSummary] = Field(default_factory=list)
    total: int = 0


class AdminStudentDetail(BaseModel):
    email: str
    display_name: Optional[str] = None
    role: str
    first_seen_at: str
    last_seen_at: str
    submissions: list[InterviewSubmission] = Field(default_factory=list)


class AdminAnalyticsResponse(BaseModel):
    student_count: int = 0
    teacher_count: int = 0
    submissions_total: int = 0
    submissions_pending: int = 0
    submissions_reviewed: int = 0
    avg_gesture_score: Optional[int] = None
    avg_teacher_score: Optional[int] = None
    avg_combined_score: Optional[int] = None


class LeaderboardEntry(BaseModel):
    email: str
    display_name: Optional[str] = None
    attempts: int = 0
    best_score: int = 0
    avg_score: int = 0


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry] = Field(default_factory=list)
    total: int = 0
