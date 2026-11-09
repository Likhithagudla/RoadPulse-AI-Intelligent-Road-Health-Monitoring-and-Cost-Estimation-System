"""
RoadPulse AI - Models Bridge (Backward Compatibility)
Delegates to backend.app.models.
"""

from app.models import (
    Base,
    User,
    RoadDefect,
    Survey,
    Road,
    WorkOrder,
    SORRate,
    RepairRecord,
)

__all__ = [
    "Base",
    "User",
    "RoadDefect",
    "Survey",
    "Road",
    "WorkOrder",
    "SORRate",
    "RepairRecord",
]
