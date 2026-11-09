"""
RoadPulse AI - Road Defect Model
Tracks detected defects with GPS geometry, bounding boxes, polygon masks,
physical severity, and detailed civil engineering repair costs.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text,
    ForeignKey, JSON, CheckConstraint, Index
)
from sqlalchemy.orm import relationship

from ..core.database import Base


class RoadDefect(Base):
    """Pavement distress detection and life-cycle workflow record."""
    __tablename__ = "road_defects"
    __table_args__ = (
        CheckConstraint("severity IN ('Low', 'Medium', 'High', 'N/A')", name="check_valid_severity"),
        CheckConstraint("status IN ('reported', 'assigned', 'in_progress', 'completed')", name="check_valid_defect_status"),
        Index("ix_defects_defect_resolved", "is_defect", "is_resolved"),
        Index("ix_defects_road_status", "road_name", "status"),
        Index("ix_defects_geo", "latitude", "longitude"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Road Info
    road_name = Column(String(128), index=True, nullable=True)
    road_id = Column(String(64), index=True, nullable=True)
    state = Column(String(64), index=True, nullable=True)
    chainage = Column(Float, nullable=True)  # Distance in meters from start

    # GPS Location
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Defect Details
    defect_type = Column(String(64), index=True, nullable=False)  # e.g., "Pothole", "Traffic_Sign"
    severity = Column(String(16), index=True, default="Low", nullable=False)
    confidence = Column(Float, nullable=False)  # AI confidence score (0-1)

    # Bounding Box (pixels)
    bbox_x1 = Column(Float, nullable=True)
    bbox_y1 = Column(Float, nullable=True)
    bbox_x2 = Column(Float, nullable=True)
    bbox_y2 = Column(Float, nullable=True)

    # Area & Cost
    estimated_area_sqm = Column(Float, nullable=True)
    repair_cost = Column(Float, default=0.0, nullable=False)
    repair_description = Column(String(255), nullable=True)
    sor_rate_per_sqm = Column(Float, nullable=True)

    # Rich Engineering Analytics (JSON payloads)
    detailed_cost_breakdown = Column(JSON, nullable=True)
    geometry_calibration = Column(JSON, nullable=True)
    severity_details = Column(JSON, nullable=True)

    # Metadata & Media
    image_path = Column(String(512), nullable=True)
    annotated_image_path = Column(String(512), nullable=True)
    vibration_level = Column(Float, nullable=True)

    # Video Context
    video_path = Column(String(512), nullable=True)
    frame_number = Column(Integer, nullable=True)
    time_seconds = Column(Float, nullable=True)
    polygon = Column(JSON, nullable=True)

    # Lifecycle & Workflow
    status = Column(String(32), default="reported", index=True, nullable=False)
    reported_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    is_defect = Column(Boolean, default=True, index=True, nullable=False)
    is_resolved = Column(Boolean, default=False, index=True, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Foreign Keys & Relationships
    survey_id = Column(Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=True)
    survey = relationship("Survey", back_populates="defects")
    reporter = relationship("User", foreign_keys=[reported_by], back_populates="reported_defects")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_defects")
    work_order = relationship("WorkOrder", back_populates="issue", uselist=False)
