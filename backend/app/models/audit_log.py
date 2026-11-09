"""
RoadPulse AI - Audit Log Model
Records system actions, security events, status updates, and administrative operations.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship

from ..core.database import Base


class AuditLog(Base):
    """Immutable audit trail for regulatory compliance and enterprise security tracking."""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_user_action", "user_id", "action"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)  # LOGIN, DETECT, ASSIGN_WORK, APPROVE_REPAIR, etc.
    entity_type = Column(String(64), nullable=True)          # defect, repair, survey, user, system
    entity_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", backref="audit_logs")
