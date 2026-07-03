"""Admin panel HTTP routes (teacher-only).

The frontend Admin Panel calls these to list submissions, fetch one with
the rubric form, and post a review. All endpoints require the caller's
email to be in `TEACHER_EMAILS` (enforced by `require_teacher`).
"""
