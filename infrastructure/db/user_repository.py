"""Postgres-backed user repository."""
from __future__ import annotations

from typing import Any

from domain.user import User


class PostgresUserRepository:
    """Manages user persistence in Postgres."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def create(self, *, email: str, password_hash: str | None = None, google_id: str | None = None) -> User:
        row = self.connection.execute(
            """
            INSERT INTO users (email, password_hash, google_id)
            VALUES (%s, %s, %s)
            RETURNING id, email, password_hash, google_id, created_at
            """,
            (email, password_hash, google_id),
        ).fetchone()
        return _user_from_row(row)

    def find_by_email(self, email: str) -> User | None:
        row = self.connection.execute(
            "SELECT id, email, password_hash, google_id, created_at FROM users WHERE email = %s",
            (email,),
        ).fetchone()
        return _user_from_row(row) if row else None

    def find_by_id(self, user_id: str) -> User | None:
        row = self.connection.execute(
            "SELECT id, email, password_hash, google_id, created_at FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
        return _user_from_row(row) if row else None

    def find_by_google_id(self, google_id: str) -> User | None:
        row = self.connection.execute(
            "SELECT id, email, password_hash, google_id, created_at FROM users WHERE google_id = %s",
            (google_id,),
        ).fetchone()
        return _user_from_row(row) if row else None

    def link_google_id(self, user_id: str, google_id: str) -> None:
        self.connection.execute(
            "UPDATE users SET google_id = %s WHERE id = %s",
            (google_id, user_id),
        )


def _user_from_row(row: dict) -> User:
    return User(
        id=str(row["id"]),
        email=row["email"],
        password_hash=row.get("password_hash"),
        google_id=row.get("google_id"),
        created_at=row.get("created_at"),
    )
