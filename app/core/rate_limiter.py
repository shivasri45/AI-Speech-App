"""Simple in-memory rate limiter for API endpoints.

For production with multiple workers, use Redis-backed slowapi.
This lightweight version works for single-instance deployments.
"""

import time
from collections import defaultdict, deque
from typing import Optional
from fastapi import HTTPException, Request

from app.auth import User


class InMemoryRateLimiter:
    """Sliding window rate limiter (per user or IP)."""
    
    def __init__(self):
        # {key: deque of timestamps}
        self._buckets: dict[str, deque] = defaultdict(deque)
    
    def check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Return True if request allowed, False if rate limited."""
        now = time.time()
        cutoff = now - window_seconds
        
        bucket = self._buckets[key]
        # Remove old timestamps
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        
        if len(bucket) >= max_requests:
            return False
        
        bucket.append(now)
        return True
    
    def remaining(self, key: str, max_requests: int) -> int:
        """Get remaining requests for a key."""
        return max(0, max_requests - len(self._buckets.get(key, [])))


limiter = InMemoryRateLimiter()


def rate_limit_user(user: User, max_requests: int = 20, window_seconds: int = 60):
    """Rate limit dependency - raises 429 if user exceeded quota.
    
    Usage:
        @router.post("/analyze")
        async def analyze(user: User = Depends(require_user)):
            rate_limit_user(user, max_requests=10)
            ...
    """
    key = f"user:{user.uid}"
    if not limiter.check(key, max_requests, window_seconds):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Too many requests. Max {max_requests} per {window_seconds}s.",
                "retry_after": window_seconds,
            },
        )
