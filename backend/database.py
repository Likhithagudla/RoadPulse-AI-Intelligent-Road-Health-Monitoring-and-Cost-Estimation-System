"""
RoadPulse AI - Database Bridge (Backward Compatibility)
Delegates to backend.app.core.database.
"""

from app.core.database import (
    engine,
    SessionLocal,
    Base,
    get_db,
)

__all__ = ["engine", "SessionLocal", "Base", "get_db"]
