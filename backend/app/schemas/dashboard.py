"""
RoadPulse AI - Dashboard Analytics Schemas
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_defects: int
    critical_defects: int
    resolved_defects: int
    pending_defects: int
    total_repair_cost: float
    total_surveys: int
    total_roads_surveyed: int
    average_pci: float
    defect_types_breakdown: Dict[str, int]
    severity_breakdown: Dict[str, int]
    cost_by_severity: Dict[str, float]


class TrendPoint(BaseModel):
    date: str
    count: int
    cost: float


class FilterValues(BaseModel):
    defect_types: List[str]
    severities: List[str]
    roads: List[str]
    states: List[str]
    statuses: List[str]
