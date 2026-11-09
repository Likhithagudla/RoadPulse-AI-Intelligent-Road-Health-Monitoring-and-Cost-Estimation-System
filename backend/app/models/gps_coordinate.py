"""
RoadPulse AI - GPS Coordinate Model
Stores high-resolution geographic waypoints, survey routes, and telemetry tracks.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from ..core.database import Base


class GPSCoordinate(Base):
    """High-frequency GPS track point captured during vehicular or mobile surveys."""
    __tablename__ = "gps_coordinates"
    __table_args__ = (
        Index("ix_gps_survey_timestamp", "survey_id", "timestamp"),
        Index("ix_gps_coords", "latitude", "longitude"),
    )

    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation = Column(Float, nullable=True)
    speed_kmh = Column(Float, nullable=True)
    heading_deg = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    survey = relationship("Survey", backref="gps_tracks")
