"""
============================================================
Road AI - Enhanced Database Models
============================================================
Extended models for the full road inspection system.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
import datetime


class User(Base):
    """User for login and authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="user")  # admin, worker, user
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class RoadDefect(Base):
    """Individual road defect detection record."""
    __tablename__ = "road_defects"

    id = Column(Integer, primary_key=True, index=True)
    
    # Road Info
    road_name = Column(String, index=True)
    road_id = Column(String, index=True, nullable=True)
    state = Column(String, index=True, nullable=True)
    chainage = Column(Float)  # Distance in meters from start
    
    # GPS Location
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Defect Details
    defect_type = Column(String, index=True)  # e.g., "Pothole", "Alligator_Cracking"
    severity = Column(String, index=True)     # "Low", "Medium", "High"
    confidence = Column(Float)                # AI confidence score 0-1
    
    # Bounding Box (normalized)
    bbox_x1 = Column(Float, nullable=True)
    bbox_y1 = Column(Float, nullable=True)
    bbox_x2 = Column(Float, nullable=True)
    bbox_y2 = Column(Float, nullable=True)
    
    # Area & Cost
    estimated_area_sqm = Column(Float, nullable=True)
    repair_cost = Column(Float, default=0.0)
    repair_description = Column(String, nullable=True)
    sor_rate_per_sqm = Column(Float, nullable=True)
    
    # Metadata
    image_path = Column(String, nullable=True)
    annotated_image_path = Column(String, nullable=True)
    vibration_level = Column(Float, nullable=True)
    
    # Video Context
    video_path = Column(String, nullable=True)
    frame_number = Column(Integer, nullable=True)
    time_seconds = Column(Float, nullable=True)
    polygon = Column(JSON, nullable=True)
    
    # Lifecycle & Workflow
    status = Column(String, default="reported") # reported, assigned, in_progress, completed
    reported_by = Column(Integer, ForeignKey("users.id"), nullable=True) # null = anonymous
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    is_defect = Column(Boolean, default=True)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    
    # Link to survey
    survey_id = Column(Integer, ForeignKey("surveys.id"), nullable=True)
    survey = relationship("Survey", back_populates="defects")

class WorkOrder(Base):
    """Tracks assignments for workers."""
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("road_defects.id"))
    assigned_to = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="assigned") # assigned, in_progress, completed
    admin_notes = Column(Text, nullable=True)
    worker_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    issue = relationship("RoadDefect")
    worker = relationship("User")


class Survey(Base):
    """A road survey session (one drive along a road)."""
    __tablename__ = "surveys"

    id = Column(Integer, primary_key=True, index=True)
    
    # Survey Info
    road_name = Column(String, index=True)
    road_id = Column(String, nullable=True)
    state = Column(String, nullable=True)
    road_type = Column(String, nullable=True)
    start_chainage = Column(Float, default=0.0)
    end_chainage = Column(Float, default=0.0)
    total_length_km = Column(Float, default=0.0)
    
    # GPS Bounds
    start_latitude = Column(Float, nullable=True)
    start_longitude = Column(Float, nullable=True)
    end_latitude = Column(Float, nullable=True)
    end_longitude = Column(Float, nullable=True)
    
    # Survey Data
    surveyor_name = Column(String, nullable=True)
    vehicle_id = Column(String, nullable=True)
    survey_date = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Video/Media
    video_path = Column(String, nullable=True)
    
    # Results Summary
    total_defects = Column(Integer, default=0)
    total_repair_cost = Column(Float, default=0.0)
    road_condition = Column(String, default="Not Assessed")  # Good, Average, Bad
    pci_score = Column(Float, nullable=True)  # Pavement Condition Index 0-100
    
    # Status
    status = Column(String, default="pending")  # pending, processing, completed, failed
    
    # Relationships
    defects = relationship("RoadDefect", back_populates="survey")
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Road(Base):
    """Road master data."""
    __tablename__ = "roads"

    id = Column(Integer, primary_key=True, index=True)
    road_id = Column(String, unique=True, index=True)  # e.g., "MDR-22"
    road_name = Column(String)
    road_type = Column(String, nullable=True)  # NH, SH, MDR, ODR, VR
    district = Column(String, nullable=True)
    state = Column(String, nullable=True)
    total_length_km = Column(Float, default=0.0)
    
    # GPS Start/End
    start_latitude = Column(Float, nullable=True)
    start_longitude = Column(Float, nullable=True)
    end_latitude = Column(Float, nullable=True)
    end_longitude = Column(Float, nullable=True)
    
    # Current Condition
    overall_condition = Column(String, default="Not Assessed")
    last_survey_date = Column(DateTime, nullable=True)
    pci_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SORRate(Base):
    """Schedule of Rates for road repairs."""
    __tablename__ = "sor_rates"

    id = Column(Integer, primary_key=True, index=True)
    defect_type = Column(String, index=True)
    severity = Column(String)
    rate_per_sqm = Column(Float)
    description = Column(String)
    unit = Column(String, default="sqm")
    
    # Region/Year specifics
    region = Column(String, default="Default")
    financial_year = Column(String, default="2025-26")
    
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class RepairRecord(Base):
    """Tracks roads marked as repaired by surveyors, pending admin approval."""
    __tablename__ = "repair_records"

    id = Column(Integer, primary_key=True, index=True)
    road_name = Column(String, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id"), nullable=True)
    surveyor_name = Column(String, nullable=True)
    repair_date = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="pending")  # pending, approved, rejected
    admin_notes = Column(Text, nullable=True)
    defects_resolved = Column(Integer, default=0)
    cost_saved = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    survey = relationship("Survey")
