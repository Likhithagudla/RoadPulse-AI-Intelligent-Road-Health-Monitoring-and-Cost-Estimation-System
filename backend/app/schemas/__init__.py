"""
RoadPulse AI - Pydantic Schemas Package
"""

from .user import UserBase, UserRegister, UserCreateAdmin, UserLogin, UserResponse
from .token import Token, TokenPayload
from .defect import (
    BBox,
    DefectBase,
    DefectCreate,
    DefectResponse,
    DefectListResponse,
    WorkAssignment,
    StatusUpdate,
)
from .survey import SurveyCreate, SurveyStatusUpdate, SurveyResponse, SurveyListResponse
from .road import RoadCreate, RoadResponse, RoadListResponse
from .repair import RepairCreate, RepairApproval, RepairResponse, RepairListResponse
from .dashboard import DashboardStats, TrendPoint, FilterValues

__all__ = [
    "UserBase",
    "UserRegister",
    "UserCreateAdmin",
    "UserLogin",
    "UserResponse",
    "Token",
    "TokenPayload",
    "BBox",
    "DefectBase",
    "DefectCreate",
    "DefectResponse",
    "DefectListResponse",
    "WorkAssignment",
    "StatusUpdate",
    "SurveyCreate",
    "SurveyStatusUpdate",
    "SurveyResponse",
    "SurveyListResponse",
    "RoadCreate",
    "RoadResponse",
    "RoadListResponse",
    "RepairCreate",
    "RepairApproval",
    "RepairResponse",
    "RepairListResponse",
    "DashboardStats",
    "TrendPoint",
    "FilterValues",
]
