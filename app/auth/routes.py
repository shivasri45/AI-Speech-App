"""HTTP routes for the auth subsystem.

Tiny surface — just enough for the frontend to:
- confirm a token is valid (`GET /auth/me`)
- get the current user's display info

`GET /auth/me` is also where we persist the user record on every sign-in
so the admin panel can show a student list without us paying a JSONL
rewrite on every other API call.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi import Depends

from app.storage import users as users_store

from .dependencies import require_user
from .models import User


logger = logging.getLogger("auth.routes")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=User)
async def me(current_user: User = Depends(require_user)) -> User:
    """Return the authenticated caller's identity.

    Returns 401 if no/invalid token, 403 if email is not `@kiet.edu`.
    Honors `AUTH_BYPASS=true`, returning the dev user.
    Side effect: upserts the user record so we have a roster for the
    admin panel.
    """
    try:
        users_store.upsert(
            firebase_uid=current_user.uid,
            email=current_user.email,
            display_name=current_user.name or "",
            role=current_user.role,
        )
    except Exception:  # noqa: BLE001 — never break sign-in on store error
        logger.exception("Failed to upsert user record (continuing)")

    return current_user
