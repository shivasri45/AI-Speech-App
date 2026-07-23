"""User records — auto-created on first authenticated request.

This is a lightweight "users seen by the app" log. It does NOT replace
Firebase as the identity store — Firebase still owns auth — but it lets
the admin panel list every student/teacher who has ever signed in,
without iterating Firebase's user list.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from ._jsonl import append_jsonl
from ._jsonl import overwrite_jsonl
from ._jsonl import read_jsonl


class UserRecord(BaseModel):
    firebase_uid: str
    email: str
    display_name: Optional[str] = None
    role: str = "student"
    first_seen_at: str
    last_seen_at: str
    avatar_url: Optional[str] = None


_PATH = Path("outputs/users.jsonl")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class UsersStore:
    """Read/write the users JSONL.

    Concurrency note: every write is a full rewrite (small file, simpler
    semantics than incremental upserts). Fine for hundreds of users; revisit
    when migrating to a real DB.
    """

    path: Path

    def __init__(self, path: Path = _PATH):
        self.path = path

    # --- Read ---

    def list_all(self) -> list[UserRecord]:
        raw = read_jsonl(self.path)
        out: list[UserRecord] = []
        for row in raw:
            try:
                out.append(UserRecord(**row))
            except Exception:
                continue
        return out

    def list_by_role(self, role: str) -> list[UserRecord]:
        return [u for u in self.list_all() if u.role == role]

    def get_by_email(self, email: str) -> Optional[UserRecord]:
        normalized = email.lower()
        for user in self.list_all():
            if user.email.lower() == normalized:
                return user
        return None

    def get_by_uid(self, firebase_uid: str) -> Optional[UserRecord]:
        for user in self.list_all():
            if user.firebase_uid == firebase_uid:
                return user
        return None

    def avatar_url_for(self, firebase_uid: str) -> Optional[str]:
        """Best-effort avatar URL lookup by uid. Never raises."""
        try:
            record = self.get_by_uid(firebase_uid)
            return record.avatar_url if record else None
        except Exception:
            return None

    # --- Write ---

    def upsert(
        self,
        firebase_uid: str,
        email: str,
        display_name: Optional[str],
        role: str,
    ) -> UserRecord:
        """Insert or update by `firebase_uid`. Returns the resulting record."""
        users = self.list_all()
        now = _now()
        found_index: Optional[int] = None
        for index, user in enumerate(users):
            if user.firebase_uid == firebase_uid:
                found_index = index
                break

        if found_index is not None:
            existing = users[found_index]
            updated = existing.model_copy(
                update={
                    "email": email.lower(),
                    "display_name": display_name or existing.display_name,
                    "role": role,
                    "last_seen_at": now,
                }
            )
            users[found_index] = updated
            overwrite_jsonl(self.path, [u.model_dump() for u in users])
            return updated

        new_record = UserRecord(
            firebase_uid=firebase_uid,
            email=email.lower(),
            display_name=display_name,
            role=role,
            first_seen_at=now,
            last_seen_at=now,
        )
        # Use append for the fast path so the common case (existing user,
        # already in the file) doesn't pay a full rewrite cost.
        append_jsonl(self.path, new_record.model_dump())
        return new_record

    def set_avatar(
        self,
        firebase_uid: str,
        avatar_url: Optional[str],
    ) -> Optional[UserRecord]:
        """Update the stored avatar URL for a user, matched by `firebase_uid`.

        Returns the updated record, or ``None`` when the user isn't found
        (which shouldn't happen since `require_user` upserts on every
        authenticated request).
        """
        users = self.list_all()
        for index, user in enumerate(users):
            if user.firebase_uid == firebase_uid:
                updated = user.model_copy(
                    update={
                        "avatar_url": avatar_url,
                        "last_seen_at": _now(),
                    }
                )
                users[index] = updated
                overwrite_jsonl(self.path, [u.model_dump() for u in users])
                return updated
        return None


# Module-level singleton — most callers just need the default file location.
users_store = UsersStore()
