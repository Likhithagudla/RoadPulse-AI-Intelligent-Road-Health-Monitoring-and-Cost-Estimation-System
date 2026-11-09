"""
RoadPulse AI - Repair Schemas
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class RepairCreate(BaseModel):
    road_name: str
    survey_id: Optional[int] = None
    surveyor_name: Optional[str] = None
    admin_notes: Optional[str] = None
    status: Optional[str] = "pending"
    defects_resolved: Optional[int] = 0
    cost_saved: Optional[float] = 0.0


class RepairApproval(BaseModel):
    admin_notes: Optional[str] = None


class RepairResponse(BaseModel):
    id: int
    road_name: str
    survey_id: Optional[int] = None
    surveyor_name: Optional[str] = None
    repair_date: Optional[datetime] = None
    status: str
    admin_notes: Optional[str] = None
    defects_resolved: int = 0
    cost_saved: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RepairListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    repairs: List[RepairResponse]
