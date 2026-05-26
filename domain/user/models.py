"""User domain entity."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    """An authenticated user account."""

    id: str
    email: str
    password_hash: str | None = None  # None for OAuth-only accounts
    google_id: str | None = None
    created_at: datetime | None = None
