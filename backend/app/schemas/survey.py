"""
RoadPulse AI - Survey Schemas
Data contracts for road survey creation, status updates, and reporting.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class SurveyCreate(BaseModel):
    road_name: str
    road_id: Optional[str] = None
    road_type: Optional[str] = None
    state: Optional[str] = None
    start_chainage: float = 0.0
    end_chainage: float = 0.0
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    surveyor_name: Optional[str] = None
    vehicle_id: Optional[str] = None


class SurveyStatusUpdate(BaseModel):
    status: str = Field(..., description="pending, processing, completed, failed")


class SurveyResponse(BaseModel):
    id: int
    road_name: str
    road_id: Optional[str] = None
    state: Optional[str] = None
    road_type: Optional[str] = None
    start_chainage: float = 0.0
    end_chainage: float = 0.0
    total_length_km: float = 0.0
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    end_latitude: Optional[float] = None
    end_longitude: Optional[float] = None
    surveyor_name: Optional[str] = None
    vehicle_id: Optional[str] = None
    survey_date: Optional[datetime] = None
    video_path: Optional[str] = None
    total_defects: int = 0
    total_repair_cost: float = 0.0
    road_condition: str = "Not Assessed"
    pci_score: Optional[float] = None
    status: str = "pending"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SurveyListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    surveys: List[SurveyResponse]
