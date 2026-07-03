"""Admin sub-router for debate teacher-review workflows.

Mounted at ``/admin/debates`` alongside the existing ``admin_router``
(Requirement 16.2 forbids editing ``app/admin/`` beyond wiring). Every
handler is guarded by ``require_teacher`` — non-teachers hit the same
403 shape the pronunciation / interview admin routes return.

Endpoints:

- ``GET  /admin/debates?status=pending_review`` — list of completed
  debates that still have at least one turn without a teacher override.
- ``GET  /admin/debates/{debate_id}`` — full debate record + all turns.
- ``POST /admin/debates/{debate_id}/turns/{turn_id}/review`` — persist
  a teacher override score/comment and, if the override flips the
  standings, update the winner in place (Task 8.2).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import User, require_teacher
from app.debate.schemas import (
    DebateRecord,
    DebateTurn,
    ParticipantInternal,
    TeacherReviewRequest,
)
from app.debate.scoring import compute_winner
from app.storage import debate_turns as debate_turns_store
from app.storage import debates as debates_store


router = APIRouter(prefix="/admin/debates", tags=["admin", "debate"])


# ---------------------------------------------------------------------------
# Local response shapes
# ---------------------------------------------------------------------------


class DebateSummary(BaseModel):
    """One row in ``GET /admin/debates``."""

    debate_id: str
    code: str
    motion_title: str
    completed_at: float
    # Turns whose ``teacher_override_score`` is still ``None``.
    pending_turns_count: int
    total_turns_count: int
    winner_participant_id: Optional[str] = None


class DebateDetail(BaseModel):
    """Response body for ``GET /admin/debates/{debate_id}``."""

    debate: DebateRecord
    turns: list[DebateTurn]


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


@router.get("", response_model=list[DebateSummary])
async def list_debates(
    status: Optional[str] = None,
    current_user: User = Depends(require_teacher),
) -> list[DebateSummary]:
    """List debates for the admin panel.

    Currently only the ``pending_review`` filter is meaningful; any other
    value (or ``None``) falls back to the same pending list for MVP.
    Future filters can be added here without touching call sites.
    """
    if status == "pending_review":
        records = debates_store.list_pending_review_debates()
    else:
        records = debates_store.list_pending_review_debates()

    summaries: list[DebateSummary] = []
    for record in records:
        turns = debate_turns_store.list_turns_for_debate(record.debate_id)
        pending = sum(1 for t in turns if t.teacher_override_score is None)
        summaries.append(
            DebateSummary(
                debate_id=record.debate_id,
                code=record.code,
                motion_title=record.motion_title,
                completed_at=record.completed_at,
                pending_turns_count=pending,
                total_turns_count=len(turns),
                winner_participant_id=record.winner_participant_id,
            )
        )
    return summaries


@router.get("/{debate_id}", response_model=DebateDetail)
async def get_debate(
    debate_id: str,
    current_user: User = Depends(require_teacher),
) -> DebateDetail:
    record = debates_store.load_debate(debate_id)
    if record is None:
        raise HTTPException(status_code=404, detail="debate_not_found")
    turns = debate_turns_store.list_turns_for_debate(debate_id)
    return DebateDetail(debate=record, turns=turns)


@router.post(
    "/{debate_id}/turns/{turn_id}/review",
    response_model=DebateTurn,
)
async def review_turn(
    debate_id: str,
    turn_id: str,
    body: TeacherReviewRequest,
    current_user: User = Depends(require_teacher),
) -> DebateTurn:
    """Persist a teacher override for a single turn.

    Pydantic already enforces ``body.score ∈ [0, 100]`` via ``Field(ge=0,
    le=100)`` on ``TeacherReviewRequest`` — an out-of-range value raises
    ``ValidationError`` before this handler runs, which FastAPI turns
    into HTTP 422 with a body naming ``score`` (Req 10.6).
    """
    updated = debate_turns_store.apply_teacher_review(
        turn_id=turn_id,
        score=body.score,
        comment=body.comment,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="turn_not_found")

    # Task 8.2 — recompute the winner in case this override flips the
    # standings. We reconstruct minimal ``ParticipantInternal`` stubs
    # from the record's snapshot dicts; only ``participant_id`` is
    # consulted by ``compute_winner`` but pydantic still requires the
    # other fields, so we pass safe placeholders for those.
    record = debates_store.load_debate(debate_id)
    if record is None:
        return updated

    all_turns = debate_turns_store.list_turns_for_debate(debate_id)
    participants = [
        ParticipantInternal(
            participant_id=str(p.get("participant_id", "")),
            user_id=str(p.get("user_id", "")),
            user_email="",  # not consulted by compute_winner
            display_name=str(p.get("display_name", "")),
            joined_at=record.created_at,
            is_ready=True,
            turn_index=int(p.get("turn_index", 0)),
            is_forfeit=bool(p.get("is_forfeit", False)),
        )
        for p in record.participants
        if isinstance(p, dict)
    ]
    new_winner_id = compute_winner(all_turns, participants)
    if new_winner_id != record.winner_participant_id:
        debates_store.update_winner(debate_id, new_winner_id)

    return updated
