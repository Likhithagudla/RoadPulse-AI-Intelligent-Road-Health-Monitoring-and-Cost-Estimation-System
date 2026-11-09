"""
RoadPulse AI - User Model
Implements role-based identity, authentication attributes, and database constraints.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, CheckConstraint, Index
from sqlalchemy.orm import relationship

from ..core.database import Base


class User(Base):
    """System user with role-based access control (Admin, Worker, User)."""
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'worker', 'user')", name="check_valid_user_role"),
        Index("ix_users_username_lower", "username"),
    )

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), default="user", nullable=False)  # admin, worker, user
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    reported_defects = relationship("RoadDefect", foreign_keys="RoadDefect.reported_by", back_populates="reporter")
    assigned_defects = relationship("RoadDefect", foreign_keys="RoadDefect.assigned_to", back_populates="assignee")
    work_orders = relationship("WorkOrder", back_populates="worker")
