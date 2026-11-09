"""
RoadPulse AI - Road Master Model
Stores official road master records, geographical classification, and condition history.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Index

from ..core.database import Base


class Road(Base):
    """Road master data repository."""
    __tablename__ = "roads"
    __table_args__ = (
        Index("ix_roads_type_state", "road_type", "state"),
    )

    id = Column(Integer, primary_key=True, index=True)
    road_id = Column(String(64), unique=True, index=True, nullable=False)  # e.g., "NH-48", "MDR-22"
    road_name = Column(String(128), index=True, nullable=False)
    road_type = Column(String(32), nullable=True)  # NH, SH, MDR, ODR, VR
    district = Column(String(64), nullable=True)
    state = Column(String(64), nullable=True)
    total_length_km = Column(Float, default=0.0, nullable=False)

    # GPS Boundary
    start_latitude = Column(Float, nullable=True)
    start_longitude = Column(Float, nullable=True)
    end_latitude = Column(Float, nullable=True)
    end_longitude = Column(Float, nullable=True)

    # Condition & Assessment
    overall_condition = Column(String(32), default="Not Assessed", nullable=False)
    last_survey_date = Column(DateTime, nullable=True)
    pci_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
