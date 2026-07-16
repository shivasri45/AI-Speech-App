"""CSV export routes for admin analytics."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Response

from app.auth import User, require_teacher
from app.storage import submissions_store, users_store
from app.storage import debates as debates_store
from app.storage import debate_turns as debate_turns_store
from app.storage import gd_sessions as gd_sessions_store

logger = logging.getLogger("admin.export")

router = APIRouter(prefix="/admin/export", tags=["admin-export"])


def _csv_response(rows: list[list[str]], filename: str) -> Response:
    """Convert list of rows to CSV response."""
    output = io.StringIO()
    writer = csv.writer(output)
    for row in rows:
        writer.writerow(row)
    csv_content = output.getvalue()
    output.close()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/students.csv")
async def export_students_csv(
    current_user: User = Depends(require_teacher),
) -> Response:
    """Export all students with their statistics."""
    del current_user
    
    student_users = users_store.list_by_role("student")
    all_submissions = submissions_store.list_all()
    
    rows = [
        [
            "Email",
            "Display Name",
            "First Seen",
            "Last Seen",
            "Total Submissions",
            "Reviewed",
            "Avg Score",
        ]
    ]
    
    for user in student_users:
        subs = [s for s in all_submissions if s.student_email.lower() == user.email.lower()]
        reviewed = [s for s in subs if s.status == "reviewed" and s.combined_score is not None]
        avg = (
            round(sum(s.combined_score or 0 for s in reviewed) / len(reviewed))
            if reviewed
            else "N/A"
        )
        
        rows.append([
            user.email,
            user.display_name or "",
            datetime.fromtimestamp(user.first_seen_at).strftime("%Y-%m-%d %H:%M") if user.first_seen_at else "",
            datetime.fromtimestamp(user.last_seen_at).strftime("%Y-%m-%d %H:%M") if user.last_seen_at else "",
            str(len(subs)),
            str(len(reviewed)),
            str(avg),
        ])
    
    filename = f"students_{datetime.now().strftime('%Y%m%d')}.csv"
    return _csv_response(rows, filename)


@router.get("/submissions.csv")
async def export_submissions_csv(
    current_user: User = Depends(require_teacher),
) -> Response:
    """Export all interview submissions."""
    del current_user
    
    all_submissions = submissions_store.list_all()
    
    rows = [
        [
            "Submission ID",
            "Student Email",
            "Student Name",
            "Question ID",
            "Question Prompt",
            "Category",
            "Status",
            "Gesture Score",
            "Teacher Score",
            "Combined Score",
            "Submitted At",
            "Reviewed At",
        ]
    ]
    
    for s in all_submissions:
        rows.append([
            s.submission_id,
            s.student_email,
            s.student_name or "",
            s.question_id,
            s.question_prompt[:100],  # Truncate long prompts
            s.question_category,
            s.status,
            str(s.gesture_score) if s.gesture_score is not None else "",
            str(s.teacher_score) if s.teacher_score is not None else "",
            str(s.combined_score) if s.combined_score is not None else "",
            datetime.fromtimestamp(s.submitted_at).strftime("%Y-%m-%d %H:%M") if s.submitted_at else "",
            datetime.fromtimestamp(s.reviewed_at).strftime("%Y-%m-%d %H:%M") if s.reviewed_at else "",
        ])
    
    filename = f"submissions_{datetime.now().strftime('%Y%m%d')}.csv"
    return _csv_response(rows, filename)


@router.get("/debates.csv")
async def export_debates_csv(
    current_user: User = Depends(require_teacher),
) -> Response:
    """Export all completed debates."""
    del current_user
    
    all_debates = debates_store.list_all()
    
    rows = [
        [
            "Debate ID",
            "Code",
            "Motion",
            "Participant Count",
            "Winner",
            "Created At",
            "Completed At",
        ]
    ]
    
    for d in all_debates:
        winner_name = ""
        if d.winner_participant_id:
            for p in d.participants:
                if isinstance(p, dict) and p.get("participant_id") == d.winner_participant_id:
                    winner_name = p.get("display_name", "")
                    break
        
        rows.append([
            d.debate_id,
            d.code,
            d.motion_title,
            str(len(d.participants)),
            winner_name,
            datetime.fromtimestamp(d.created_at).strftime("%Y-%m-%d %H:%M") if d.created_at else "",
            datetime.fromtimestamp(d.completed_at).strftime("%Y-%m-%d %H:%M") if d.completed_at else "",
        ])
    
    filename = f"debates_{datetime.now().strftime('%Y%m%d')}.csv"
    return _csv_response(rows, filename)


@router.get("/gd_sessions.csv")
async def export_gd_sessions_csv(
    current_user: User = Depends(require_teacher),
) -> Response:
    """Export all GD sessions with participant scores."""
    del current_user
    
    from pathlib import Path
    from app.storage._jsonl import read_jsonl
    from app.gd.schemas import GDSessionRecord
    
    rows = [
        [
            "Session ID",
            "Code",
            "Topic",
            "Participant",
            "Total Score",
            "Content Quality",
            "Communication",
            "Participation",
            "Listening",
            "Leadership",
            "Rank",
            "Speech Count",
            "Speak Time (s)",
            "Interruptions",
            "Completed At",
        ]
    ]
    
    all_sessions = []
    for row in read_jsonl(Path("outputs/gd_sessions.jsonl")):
        try:
            all_sessions.append(GDSessionRecord.model_validate(row))
        except Exception:
            continue
    
    for session in all_sessions:
        for score in session.scores:
            rows.append([
                session.session_id,
                session.code,
                session.topic_title,
                score.display_name,
                str(score.total_score),
                str(score.content_quality),
                str(score.communication),
                str(score.participation),
                str(score.listening),
                str(score.leadership),
                str(score.rank),
                str(score.speech_count),
                str(round(score.total_speak_seconds, 1)),
                str(score.interruption_count),
                datetime.fromtimestamp(session.completed_at).strftime("%Y-%m-%d %H:%M") if session.completed_at else "",
            ])
    
    filename = f"gd_sessions_{datetime.now().strftime('%Y%m%d')}.csv"
    return _csv_response(rows, filename)


@router.get("/analytics_summary.csv")
async def export_analytics_summary(
    current_user: User = Depends(require_teacher),
) -> Response:
    """Export overall analytics summary."""
    del current_user
    
    from pathlib import Path
    from app.storage._jsonl import read_jsonl
    
    students = users_store.list_by_role("student")
    teachers = users_store.list_by_role("teacher")
    all_submissions = submissions_store.list_all()
    reviewed = [s for s in all_submissions if s.status == "reviewed"]
    all_debates = debates_store.list_all()
    
    gd_count = len(read_jsonl(Path("outputs/gd_sessions.jsonl")))
    
    rows = [
        ["Metric", "Value"],
        ["Report Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["Total Students", str(len(students))],
        ["Total Teachers", str(len(teachers))],
        ["Total Interview Submissions", str(len(all_submissions))],
        ["Interviews Reviewed", str(len(reviewed))],
        ["Interviews Pending", str(len(all_submissions) - len(reviewed))],
        ["Total Debates Completed", str(len(all_debates))],
        ["Total GD Sessions Completed", str(gd_count)],
    ]
    
    if reviewed:
        avg_score = sum(s.combined_score or 0 for s in reviewed) / len(reviewed)
        rows.append(["Average Interview Score", f"{avg_score:.1f}"])
    
    filename = f"analytics_summary_{datetime.now().strftime('%Y%m%d')}.csv"
    return _csv_response(rows, filename)
