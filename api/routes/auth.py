"""Authentication routes and current-user dependency."""
from __future__ import annotations

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.schemas.auth import GoogleTokenRequest, LoginRequest, RegisterRequest, TokenResponse, UserResponse
from application.auth import AuthError, AuthService
from domain.user import User
from shared.config import get_app_config
from shared.logger import get_logger, log_event

router = APIRouter(prefix="/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)
_auth_service: AuthService | None = None
_market_repo: object | None = None
_competitor_repo: object | None = None
_source_repo: object | None = None
_activity_repo: object | None = None
logger = get_logger(__name__)


def configure_auth_service(
    service: AuthService,
    market_repo: object | None = None,
    competitor_repo: object | None = None,
    source_repo: object | None = None,
    activity_repo: object | None = None,
) -> None:
    global _auth_service, _market_repo, _competitor_repo, _source_repo, _activity_repo
    _auth_service = service
    _market_repo = market_repo
    _competitor_repo = competitor_repo
    _source_repo = source_repo
    _activity_repo = activity_repo


def _get_auth_service() -> AuthService:
    if _auth_service is None:
        raise RuntimeError("AuthService not configured")
    return _auth_service


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    auth_service: AuthService = Depends(_get_auth_service),
) -> User:
    """FastAPI dependency — resolves the Bearer token to an authenticated User."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return auth_service.verify_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    try:
        token = auth_service.register(request.email, request.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    _seed_markets_for_token(token, auth_service)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    try:
        token = auth_service.login(request.email, request.password)
        return TokenResponse(access_token=token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=current_user.id, email=current_user.email)


def _seed_markets_for_token(token: str, auth_service: AuthService) -> None:
    if _market_repo is None or _competitor_repo is None or _source_repo is None:
        return
    try:
        from application.onboarding.templates import seed_template_markets
        user = auth_service.verify_token(token)
        seed_template_markets(user.id, _market_repo, _competitor_repo, _source_repo, _activity_repo)
    except Exception as exc:
        log_event(
            logger,
            "default_template_seed_failed",
            level=logging.ERROR,
            error_type=type(exc).__name__,
            error=str(exc),
        )


@router.post("/google", response_model=TokenResponse)
def google_login(
    request: GoogleTokenRequest,
    auth_service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    """Verify a Google ID token issued by the frontend and return a session JWT."""
    cfg = get_app_config()
    if not cfg.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google OAuth not configured")
    try:
        info = google_id_token.verify_oauth2_token(
            request.credential,
            google_requests.Request(),
            cfg.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token") from exc
    try:
        token = auth_service.google_login(google_id=info["sub"], email=info["email"])
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    _seed_markets_for_token(token, auth_service)
    return TokenResponse(access_token=token)
