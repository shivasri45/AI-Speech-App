"""HTTP routes for the auth subsystem.

Tiny surface — just enough for the frontend to:
- confirm a token is valid (`GET /auth/me`)
- get the current user's display info

User records are persisted by the `require_user` dependency (via
`_record_seen`) on every authenticated request, so the admin panel has a
roster without this handler needing to write anything itself.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends

from app.storage import users_store

from .dependencies import require_user
from .models import User


logger = logging.getLogger("auth.routes")

router = APIRouter(prefix="/auth", tags=["auth"])


class MeResponse(User):
    """`/auth/me` payload: the user identity plus their profile avatar.

    Extends `User` so all existing fields are preserved; adds `avatar_url`
    so the frontend header can show the current user's photo.
    """

    avatar_url: Optional[str] = None


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(require_user)) -> MeResponse:
    """Return the authenticated caller's identity plus avatar.

    Returns 401 if no/invalid token, 403 if email is not `@kiet.edu`.
    Honors `AUTH_BYPASS=true`, returning the dev user.

    The user record is upserted by the `require_user` dependency, so this
    handler just returns the identity (with the stored avatar URL).
    """
    avatar_url = users_store.avatar_url_for(current_user.uid)
    return MeResponse(**current_user.model_dump(), avatar_url=avatar_url)
