"""
RoadPulse AI - Work Order Model
Tracks maintenance and patch assignments for field workers.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import relationship

from ..core.database import Base


class WorkOrder(Base):
    """Field repair work orders dispatched to municipal/contractor road crews."""
    __tablename__ = "work_orders"
    __table_args__ = (
        CheckConstraint("status IN ('assigned', 'in_progress', 'completed', 'verified')", name="check_valid_work_order_status"),
        Index("ix_work_orders_worker_status", "assigned_to", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("road_defects.id", ondelete="CASCADE"), nullable=False, unique=True)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(32), default="assigned", index=True, nullable=False)
    admin_notes = Column(Text, nullable=True)
    worker_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    issue = relationship("RoadDefect", back_populates="work_order")
    worker = relationship("User", back_populates="work_orders")
