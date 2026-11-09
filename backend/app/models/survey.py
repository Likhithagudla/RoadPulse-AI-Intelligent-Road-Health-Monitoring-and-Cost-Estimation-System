"""
RoadPulse AI - Survey Model
Tracks mobile and dashcam road survey sessions, PCI scores, and defect summaries.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import relationship

from ..core.database import Base


class Survey(Base):
    """A road survey session (inspection drive)."""
    __tablename__ = "surveys"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="check_valid_survey_status"),
        Index("ix_surveys_road_date", "road_name", "survey_date"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Survey Info
    road_name = Column(String(128), index=True, nullable=False)
    road_id = Column(String(64), index=True, nullable=True)
    state = Column(String(64), nullable=True)
    road_type = Column(String(32), nullable=True)
    start_chainage = Column(Float, default=0.0)
    end_chainage = Column(Float, default=0.0)
    total_length_km = Column(Float, default=0.0)

    # GPS Bounds
    start_latitude = Column(Float, nullable=True)
    start_longitude = Column(Float, nullable=True)
    end_latitude = Column(Float, nullable=True)
    end_longitude = Column(Float, nullable=True)

    # Survey Metadata
    surveyor_name = Column(String(64), nullable=True)
    vehicle_id = Column(String(64), nullable=True)
    survey_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    video_path = Column(String(512), nullable=True)

    # Summary Results
    total_defects = Column(Integer, default=0, nullable=False)
    total_repair_cost = Column(Float, default=0.0, nullable=False)
    road_condition = Column(String(32), default="Not Assessed", nullable=False)
    pci_score = Column(Float, nullable=True)  # Pavement Condition Index (0-100)

    # Processing Status
    status = Column(String(32), default="pending", index=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    defects = relationship("RoadDefect", back_populates="survey", cascade="all, delete-orphan")
    repairs = relationship("RepairRecord", back_populates="survey")
