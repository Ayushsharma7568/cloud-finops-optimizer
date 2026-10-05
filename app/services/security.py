"""Security utilities for CSRF protection and session handling."""

import logging
import secrets
from flask import session

logger = logging.getLogger(__name__)


def generate_csrf_token() -> str:
    """Generate or retrieve a cryptographically secure CSRF token for the session."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validate_csrf_token(token: str | None) -> bool:
    """Validate submitted CSRF token against session token in constant time."""
    session_token = session.get("csrf_token")
    if not session_token or not token:
        return False
    return secrets.compare_digest(session_token, token)
