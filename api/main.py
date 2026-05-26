"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.dependencies import build_signal_api_dependencies
from api.routes.auth import configure_auth_service, router as auth_router
from api.routes.businesses import router as businesses_router
from api.routes.interactions import router as interactions_router
from api.routes.signals import (
    configure_signal_api_dependencies,
    router as signals_router,
)
from application.auth import AuthService
from infrastructure.db.user_repository import PostgresUserRepository
from shared.config import get_settings
from shared.logger import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(businesses_router)
app.include_router(interactions_router)
app.include_router(signals_router)


@app.on_event("startup")
async def configure_runtime_dependencies() -> None:
    """Configure runtime dependencies for API route handlers."""
    from shared.config import get_app_config
    from infrastructure.db.repository import connect_postgres
    app_config = get_app_config()
    from infrastructure.db import PostgresMarketRepository
    connection = connect_postgres(app_config.DATABASE_URL)
    configure_auth_service(
        AuthService(
            user_repository=PostgresUserRepository(connection=connection),
            secret=app_config.JWT_SECRET,
            expiry_minutes=app_config.JWT_EXPIRY_MINUTES,
        ),
        market_repo=PostgresMarketRepository(connection=connection),
    )
    configure_signal_api_dependencies(build_signal_api_dependencies())


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LidScout API",
        "version": settings.api_version,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Railway health check endpoint."""
    return {
        "status": "healthy",
        "service": "lidscout-api",
        "version": settings.api_version,
    }


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
