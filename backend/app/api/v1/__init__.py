"""
RoadPulse AI - API v1 Router Aggregator
Combines modular routers under a unified prefix.
"""

from fastapi import APIRouter

from .auth import router as auth_router
from .defects import router as defects_router
from .surveys import router as surveys_router
from .roads import router as roads_router
from .repairs import router as repairs_router
from .dashboard import router as dashboard_router
from .admin import router as admin_router
from .worker import router as worker_router

api_v1_router = APIRouter()

# Mount sub-routers
api_v1_router.include_router(auth_router)
api_v1_router.include_router(defects_router)
api_v1_router.include_router(surveys_router)
api_v1_router.include_router(roads_router)
api_v1_router.include_router(repairs_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(worker_router)

__all__ = ["api_v1_router"]
