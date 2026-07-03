"""JSONL-backed storage stores.

This package is the swap-point for moving to a real database later. Each
store exposes a small typed API so callers depend on the protocol, not
the file format. To migrate to Postgres / SQLite, swap the store
implementations behind the same interface — call sites don't change.
"""

from .reviews import InterviewReview
from .reviews import ReviewsStore
from .reviews import reviews_store
from .submissions import InterviewSubmission
from .submissions import SubmissionsStore
from .submissions import submissions_store
from .users import UserRecord
from .users import UsersStore
from .users import users_store


__all__ = [
    "InterviewReview",
    "InterviewSubmission",
    "ReviewsStore",
    "SubmissionsStore",
    "UserRecord",
    "UsersStore",
    "reviews_store",
    "submissions_store",
    "users_store",
]
