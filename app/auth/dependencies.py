"""FastAPI dependencies that gate protected endpoints on a verified user.

Usage:

    from fastapi import Depends
    from app.auth import User, require_user

    @router.post("/protected")
    async def handler(current_user: User = Depends(require_user)):
        ...

    @router.get("/admin/x")
    async def teacher_only(user: User = Depends(require_teacher)):
        ...

For WebSocket endpoints (where headers are awkward), use
`verify_token_string` directly with the `id_token` query parameter.
"""

from __future__ import annotations

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status

from app.core.config import settings

from .firebase_admin import verify_id_token
from .models import User
from .models import UserRole


# Only `@kiet.edu` accounts may use the app. Enforced on the server so the
# client-side check is purely a UX nicety.
ALLOWED_EMAIL_DOMAIN = "kiet.edu"


def _teacher_email_set() -> set[str]:
    """Parse the `TEACHER_EMAILS` setting into a lowercase set.

    Re-parsed on every call so a `.env` edit + uvicorn auto-reload picks
    up new teachers without restarting from scratch.
    """
    raw = settings.TEACHER_EMAILS or ""
    return {
        item.strip().lower()
        for item in raw.split(",")
        if item.strip()
    }


def _role_for_email(email: str) -> UserRole:
    """Resolve a user's role from the email allowlist."""
    return "teacher" if email.lower() in _teacher_email_set() else "student"


def _dev_user() -> User:
    email = f"dev@{ALLOWED_EMAIL_DOMAIN}"
    return User(
        uid="dev-user",
        email=email,
        name="Dev User",
        email_verified=True,
        role=_role_for_email(email),
    )


def _build_user_from_claims(claims: dict) -> User:
    email = (claims.get("email") or "").lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_missing_email",
        )
    # Domain restriction temporarily disabled — any Gmail user can access
    # if not email.endswith(f"@{ALLOWED_EMAIL_DOMAIN}"):
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail=f"Email must be @{ALLOWED_EMAIL_DOMAIN}",
    #     )
    uid = claims.get("uid") or claims.get("user_id") or claims.get("sub")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token_missing_uid",
        )
    return User(
        uid=str(uid),
        email=email,
        name=claims.get("name"),
        email_verified=bool(claims.get("email_verified")),
        role=_role_for_email(email),
    )


def _record_seen(user: User) -> None:
    """Upsert a row in the users JSONL so the admin panel can list every
    student/teacher who has ever signed in. Failures are swallowed —
    auth shouldn't break because of a storage hiccup."""
    try:
        # Lazy import to avoid a circular dep at module load time.
        from app.storage import users_store

        users_store.upsert(
            firebase_uid=user.uid,
            email=user.email,
            display_name=user.name,
            role=user.role,
        )
    except Exception:  # noqa: BLE001 — log + continue
        import logging

        logging.getLogger("auth.dependencies").warning(
            "users_store.upsert failed", exc_info=True
        )


async def require_user(request: Request) -> User:
    """FastAPI dependency: verify the bearer token and return the User."""
    if settings.AUTH_BYPASS:
        user = _dev_user()
        _record_seen(user)
        return user

    header = request.headers.get("Authorization") or ""
    if not header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = header[len("Bearer "):].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = verify_id_token(token)
    user = _build_user_from_claims(claims)
    _record_seen(user)
    return user


def verify_token_string(token: str) -> User:
    """Same verification as `require_user`, but for callers that already
    have the raw token string (e.g. a WebSocket query param).

    Honors `AUTH_BYPASS` for parity with `require_user`.
    """
    if settings.AUTH_BYPASS:
        return _dev_user()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty id_token",
        )
    claims = verify_id_token(token)
    return _build_user_from_claims(claims)


async def require_teacher(
    current_user: User = Depends(require_user),
) -> User:
    """Variant of `require_user` that also enforces teacher role.

    Returns 403 with a clear message when a student-role user hits an
    admin endpoint. Useful for `/admin/*` routes.
    """
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is restricted to teachers.",
        )
    return current_user
