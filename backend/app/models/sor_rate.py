"""
RoadPulse AI - Schedule of Rates (SOR) Model
Database persistence for regional Schedule of Rates applied to road repairs.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Index

from ..core.database import Base


class SORRate(Base):
    """Regional Schedule of Rates (SOR) items."""
    __tablename__ = "sor_rates"
    __table_args__ = (
        Index("ix_sor_defect_region", "defect_type", "region"),
    )

    id = Column(Integer, primary_key=True, index=True)
    defect_type = Column(String(64), index=True, nullable=False)
    severity = Column(String(16), nullable=False)
    rate_per_sqm = Column(Float, nullable=False)
    description = Column(String(255), nullable=False)
    unit = Column(String(32), default="sqm", nullable=False)

    region = Column(String(64), default="Default", index=True, nullable=False)
    financial_year = Column(String(32), default="2025-26", nullable=False)

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
