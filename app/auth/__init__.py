"""Firebase-Auth-based authentication for the speech platform.

All requests to protected endpoints must carry a Firebase ID token in the
`Authorization: Bearer <token>` header. The token is verified by
`firebase-admin` and the caller's email must end with `@kiet.edu`.

For local development without a Firebase project, set `AUTH_BYPASS=true`
to short-circuit verification and treat every request as a fake dev user.
"""

from .dependencies import ALLOWED_EMAIL_DOMAIN
from .dependencies import require_teacher
from .dependencies import require_user
from .dependencies import verify_token_string
from .firebase_admin import init_firebase_admin
from .firebase_admin import verify_id_token
from .models import User
from .models import UserRole


__all__ = [
    "ALLOWED_EMAIL_DOMAIN",
    "User",
    "UserRole",
    "init_firebase_admin",
    "require_teacher",
    "require_user",
    "verify_id_token",
    "verify_token_string",
]
