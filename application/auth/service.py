"""Authentication service — registration, login, token verification."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from domain.user import User
from infrastructure.db.user_repository import PostgresUserRepository

_ALGORITHM = "HS256"


class AuthError(Exception):
    """Raised when authentication fails."""


class AuthService:
    def __init__(
        self,
        user_repository: PostgresUserRepository,
        secret: str,
        expiry_minutes: int = 60 * 24 * 30,
    ) -> None:
        self._repo = user_repository
        self._secret = secret
        self._expiry_minutes = expiry_minutes

    def register(self, email: str, password: str) -> str:
        """Create a new account and return a JWT token."""
        email = email.strip().lower()
        if len(password) < 8:
            raise AuthError("Password must be at least 8 characters")
        if self._repo.find_by_email(email):
            raise AuthError("An account with this email already exists")
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = self._repo.create(email=email, password_hash=password_hash)
        return self._issue_token(user)

    def login(self, email: str, password: str) -> str:
        """Verify credentials and return a JWT token."""
        email = email.strip().lower()
        user = self._repo.find_by_email(email)
        if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            raise AuthError("Invalid email or password")
        return self._issue_token(user)

    def google_login(self, google_id: str, email: str) -> str:
        """Find or create a user via Google OAuth and return a JWT token."""
        user = self._repo.find_by_google_id(google_id)
        if user:
            return self._issue_token(user)
        user = self._repo.find_by_email(email)
        if user:
            self._repo.link_google_id(user.id, google_id)
            return self._issue_token(user)
        user = self._repo.create(email=email, google_id=google_id)
        return self._issue_token(user)

    def verify_token(self, token: str) -> User:
        """Decode a JWT and return the corresponding user."""
        try:
            payload = jwt.decode(token, self._secret, algorithms=[_ALGORITHM])
            user_id: str | None = payload.get("sub")
            if not user_id:
                raise AuthError("Invalid token")
        except JWTError as exc:
            raise AuthError("Invalid token") from exc
        user = self._repo.find_by_id(user_id)
        if not user:
            raise AuthError("User not found")
        return user

    def _issue_token(self, user: User) -> str:
        expiry = datetime.now(UTC) + timedelta(minutes=self._expiry_minutes)
        return jwt.encode(
            {"sub": user.id, "email": user.email, "exp": expiry},
            self._secret,
            algorithm=_ALGORITHM,
        )
