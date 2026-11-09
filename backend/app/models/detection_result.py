"""
RoadPulse AI - Detection Result Model
Normalized record for raw and calibrated AI defect instance detections.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship

from ..core.database import Base


class DetectionResult(Base):
    """Raw and processed AI inference detection instance."""
    __tablename__ = "detection_results"
    __table_args__ = (
        Index("ix_detection_defect_class", "defect_id", "class_name"),
        Index("ix_detection_confidence", "confidence"),
        Index("ix_detection_severity", "severity"),
    )

    id = Column(Integer, primary_key=True, index=True)
    defect_id = Column(Integer, ForeignKey("road_defects.id", ondelete="CASCADE"), nullable=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=True, index=True)
    class_id = Column(Integer, nullable=False)
    class_name = Column(String(64), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    bbox_x1 = Column(Float, nullable=False)
    bbox_y1 = Column(Float, nullable=False)
    bbox_x2 = Column(Float, nullable=False)
    bbox_y2 = Column(Float, nullable=False)
    area_sqm = Column(Float, nullable=True)
    severity = Column(String(16), nullable=False)
    is_defect = Column(Boolean, default=True, nullable=False)
    geometry_metadata = Column(JSON, nullable=True)
    cost_metadata = Column(JSON, nullable=True)
    raw_polygon = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    defect = relationship("RoadDefect", backref="detections")
    survey = relationship("Survey", backref="detections")
