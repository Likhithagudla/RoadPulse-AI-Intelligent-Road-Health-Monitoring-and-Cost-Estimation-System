"""
RoadPulse AI - Enterprise FastAPI Application Factory
Initializes FastAPI, mounts security/logging middlewares, static assets, and modular API routers.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse

from .core.config import settings
from .core.database import engine, Base, SessionLocal
from .core.security import SecurityService
from .models.user import User
from .middleware.logging_middleware import RequestLoggingMiddleware
from .middleware.rate_limiter import AuthRateLimitMiddleware
from .middleware.error_handler import register_exception_handlers
from .api.v1 import api_v1_router


def seed_default_accounts() -> None:
    """Provisions default baseline user accounts if the database is freshly initialized."""
    db = SessionLocal()
    try:
        defaults = [
            {"username": "admin", "password": "AdminPassword123!", "role": "admin"},
            {"username": "worker1", "password": "WorkerPassword123!", "role": "worker"},
            {"username": "user1", "password": "UserPassword123!", "role": "user"},
        ]
        for acct in defaults:
            existing = db.query(User).filter(User.username == acct["username"]).first()
            if not existing:
                print(f"[INIT] Seeding baseline account: {acct['username']} ({acct['role']})")
                user = User(
                    username=acct["username"],
                    password_hash=SecurityService.get_password_hash(acct["password"]),
                    role=acct["role"],
                    is_active=True,
                )
                db.add(user)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[WARN] Failed seeding default accounts: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: initialize database tables and baseline assets."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    seed_default_accounts()
    yield


def create_app() -> FastAPI:
    """Builds and configures the FastAPI application instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Enterprise AI Intelligent Road Health Monitoring & Cost Estimation System",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # 1. Register Global Exception Handlers
    register_exception_handlers(app)

    # 2. Middlewares (Reverse order of execution: RateLimit -> Logging -> CORS)
    app.add_middleware(AuthRateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Mount Static Files
    upload_dir = settings.upload_path
    app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

    dashboard_dir = settings.dashboard_path
    if dashboard_dir.exists():
        app.mount("/dashboard", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard")

    # 4. Include Modular API Routers
    app.include_router(api_v1_router, prefix=settings.API_V1_STR)

    # 5. Standard Health Check Endpoint (for Kubernetes / Docker / AWS ALB)
    @app.get("/health", tags=["Health & Diagnostics"])
    @app.get("/api/health", tags=["Health & Diagnostics"])
    def health_check():
        """Standard health check endpoint for container orchestrators and load balancers."""
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
        }

    # 6. Root and Favicon endpoints
    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return Response(status_code=204)

    @app.get("/", include_in_schema=False)
    def root():
        if dashboard_dir.exists():
            return RedirectResponse(url="/dashboard/")
        return JSONResponse({
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "api_documentation": "/docs",
            "health_status": "/health",
        })

    return app


app = create_app()
