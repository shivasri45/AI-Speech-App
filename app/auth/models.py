"""Pydantic models for the authenticated user."""

from __future__ import annotations

from pydantic import BaseModel


from typing import Literal


UserRole = Literal["student", "teacher"]


class User(BaseModel):
    """The minimal user identity threaded through protected handlers."""

    uid: str
    email: str
    name: str | None = None
    email_verified: bool = False
    role: UserRole = "student"

    @property
    def is_teacher(self) -> bool:
        return self.role == "teacher"
