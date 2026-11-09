"""
RoadPulse AI - Repair Record Model
Tracks repairs submitted by field workers/surveyors, requiring administrator verification and approval.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import relationship

from ..core.database import Base


class RepairRecord(Base):
    """Tracks completed road repairs pending administrative approval."""
    __tablename__ = "repair_records"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="check_valid_repair_status"),
        Index("ix_repairs_status_date", "status", "repair_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    road_name = Column(String(128), index=True, nullable=False)
    survey_id = Column(Integer, ForeignKey("surveys.id", ondelete="SET NULL"), nullable=True)
    surveyor_name = Column(String(64), nullable=True)
    repair_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(String(32), default="pending", index=True, nullable=False)  # pending, approved, rejected
    admin_notes = Column(Text, nullable=True)
    defects_resolved = Column(Integer, default=0, nullable=False)
    cost_saved = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    survey = relationship("Survey", back_populates="repairs")
