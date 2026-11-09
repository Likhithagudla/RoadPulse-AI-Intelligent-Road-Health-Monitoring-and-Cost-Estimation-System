"""
RoadPulse AI - Road Defect Schemas
Request and response models for road distress records.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class BBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class DefectBase(BaseModel):
    road_name: Optional[str] = None
    road_id: Optional[str] = None
    state: Optional[str] = None
    chainage: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    defect_type: str
    severity: str = "Low"
    confidence: float
    estimated_area_sqm: Optional[float] = None
    repair_cost: float = 0.0
    repair_description: Optional[str] = None
    sor_rate_per_sqm: Optional[float] = None
    vibration_level: Optional[float] = None
    is_defect: bool = True


class DefectCreate(DefectBase):
    bbox: Optional[BBox] = None
    polygon: Optional[List[List[float]]] = None
    image_path: Optional[str] = None
    annotated_image_path: Optional[str] = None
    video_path: Optional[str] = None
    frame_number: Optional[int] = None
    time_seconds: Optional[float] = None
    survey_id: Optional[int] = None
    detailed_cost_breakdown: Optional[Dict[str, Any]] = None
    geometry_calibration: Optional[Dict[str, Any]] = None
    severity_details: Optional[Dict[str, Any]] = None


class DefectResponse(BaseModel):
    id: int
    road_name: Optional[str] = None
    road_id: Optional[str] = None
    state: Optional[str] = None
    chainage: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    defect_type: str
    severity: str
    confidence: float
    estimated_area_sqm: Optional[float] = None
    repair_cost: float = 0.0
    repair_description: Optional[str] = None
    sor_rate_per_sqm: Optional[float] = None
    image_path: Optional[str] = None
    annotated_image_path: Optional[str] = None
    video_path: Optional[str] = None
    frame_number: Optional[int] = None
    time_seconds: Optional[float] = None
    polygon: Optional[List[Any]] = None
    timestamp: Optional[datetime] = None
    is_defect: bool = True
    is_resolved: bool = False
    status: str = "reported"
    reported_by: Optional[int] = None
    assigned_to: Optional[int] = None
    survey_id: Optional[int] = None
    detailed_cost_breakdown: Optional[Dict[str, Any]] = None
    geometry_calibration: Optional[Dict[str, Any]] = None
    severity_details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class DefectListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    defects: List[DefectResponse]


class WorkAssignment(BaseModel):
    issue_id: int
    worker_id: int
    notes: Optional[str] = None


class StatusUpdate(BaseModel):
    issue_id: int
    status: str = Field(..., description="reported, assigned, in_progress, completed")
    notes: Optional[str] = None
