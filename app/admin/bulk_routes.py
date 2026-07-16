"""Bulk actions and administrative controls for teachers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import User, require_teacher
from app.storage import submissions_store
from app.storage._jsonl import read_jsonl, overwrite_jsonl

logger = logging.getLogger("admin.bulk")

router = APIRouter(prefix="/admin", tags=["admin-bulk"])


class BulkDeleteRequest(BaseModel):
    submission_ids: List[str]


class BulkDeleteResponse(BaseModel):
    deleted_count: int
    failed_ids: List[str]


@router.post("/submissions/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_submissions(
    body: BulkDeleteRequest,
    current_user: User = Depends(require_teacher),
) -> BulkDeleteResponse:
    """Delete multiple submissions at once."""
    logger.info(
        f"Teacher {current_user.email} bulk-deleting {len(body.submission_ids)} submissions"
    )
    
    if not body.submission_ids:
        return BulkDeleteResponse(deleted_count=0, failed_ids=[])
    
    submissions_path = Path("outputs/interview_submissions.jsonl")
    rows = read_jsonl(submissions_path)
    
    to_delete = set(body.submission_ids)
    deleted = []
    kept = []
    
    for row in rows:
        sub_id = row.get("submission_id")
        if sub_id in to_delete:
            deleted.append(sub_id)
        else:
            kept.append(row)
    
    overwrite_jsonl(submissions_path, kept)
    
    # Also delete related reviews
    reviews_path = Path("outputs/interview_reviews.jsonl")
    if reviews_path.exists():
        review_rows = read_jsonl(reviews_path)
        review_kept = [
            r for r in review_rows
            if r.get("submission_id") not in to_delete
        ]
        overwrite_jsonl(reviews_path, review_kept)
    
    failed = [sid for sid in body.submission_ids if sid not in deleted]
    
    return BulkDeleteResponse(
        deleted_count=len(deleted),
        failed_ids=failed,
    )


@router.delete("/submissions/{submission_id}")
async def delete_single_submission(
    submission_id: str,
    current_user: User = Depends(require_teacher),
) -> dict:
    """Delete a single submission and its review."""
    logger.info(f"Teacher {current_user.email} deleting submission {submission_id}")
    
    submissions_path = Path("outputs/interview_submissions.jsonl")
    rows = read_jsonl(submissions_path)
    
    original_count = len(rows)
    kept = [r for r in rows if r.get("submission_id") != submission_id]
    
    if len(kept) == original_count:
        raise HTTPException(status_code=404, detail="submission_not_found")
    
    overwrite_jsonl(submissions_path, kept)
    
    # Delete related review
    reviews_path = Path("outputs/interview_reviews.jsonl")
    if reviews_path.exists():
        review_rows = read_jsonl(reviews_path)
        review_kept = [r for r in review_rows if r.get("submission_id") != submission_id]
        overwrite_jsonl(reviews_path, review_kept)
    
    return {"deleted": True, "submission_id": submission_id}


class StorageStats(BaseModel):
    total_submissions: int
    reviewed: int
    pending: int
    total_debates: int
    total_gd_sessions: int
    total_students: int
    storage_size_mb: float


@router.get("/storage-stats", response_model=StorageStats)
async def get_storage_stats(
    current_user: User = Depends(require_teacher),
) -> StorageStats:
    """Get storage statistics."""
    del current_user
    
    from app.storage import users_store
    
    outputs_dir = Path("outputs")
    total_size = 0
    if outputs_dir.exists():
        for f in outputs_dir.glob("**/*"):
            if f.is_file():
                total_size += f.stat().st_size
    
    all_subs = submissions_store.list_all()
    reviewed = [s for s in all_subs if s.status == "reviewed"]
    
    from app.storage import debates as debates_store
    all_debates = debates_store.list_all()
    
    gd_count = len(read_jsonl(Path("outputs/gd_sessions.jsonl")))
    students = users_store.list_by_role("student")
    
    return StorageStats(
        total_submissions=len(all_subs),
        reviewed=len(reviewed),
        pending=len(all_subs) - len(reviewed),
        total_debates=len(all_debates),
        total_gd_sessions=gd_count,
        total_students=len(students),
        storage_size_mb=round(total_size / (1024 * 1024), 2),
    )
