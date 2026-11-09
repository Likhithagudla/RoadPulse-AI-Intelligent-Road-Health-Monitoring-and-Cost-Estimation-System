"""
RoadPulse AI - Road Master Schemas
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class RoadCreate(BaseModel):
    road_id: str
    road_name: str
    road_type: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    total_length_km: float = 0.0
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    end_latitude: Optional[float] = None
    end_longitude: Optional[float] = None


class RoadResponse(BaseModel):
    id: int
    road_id: str
    road_name: str
    road_type: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    total_length_km: float = 0.0
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    end_latitude: Optional[float] = None
    end_longitude: Optional[float] = None
    overall_condition: str = "Not Assessed"
    last_survey_date: Optional[datetime] = None
    pci_score: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RoadListResponse(BaseModel):
    total: int
    roads: List[RoadResponse]
