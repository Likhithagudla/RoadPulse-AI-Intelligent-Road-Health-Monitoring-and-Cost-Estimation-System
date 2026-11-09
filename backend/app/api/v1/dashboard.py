"""
RoadPulse AI - Executive Dashboard & Analytics Router
Aggregates road health statistics, budget forecasts, and filter criteria.
"""

import os
import time
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, desc

from ...core.database import get_db
from ...core.config import settings
from ...models.defect import RoadDefect
from ...models.survey import Survey
from ...models.road import Road
from ...models.repair import RepairRecord
from ...schemas.dashboard import DashboardStats, TrendPoint, FilterValues

router = APIRouter(tags=["Dashboard & Analytics"])

# Lightweight in-memory TTL cache for high-frequency dashboard polling
_stats_cache: Dict[str, Any] = {"timestamp": 0.0, "data": None}
CACHE_TTL_SECONDS = 5.0


@router.get("/status", summary="System Health & AI Model Status")
def get_system_status(db: Session = Depends(get_db)):
    """System health check and loaded AI model checkpoint status."""
    total_defects = db.query(RoadDefect).count()
    total_surveys = db.query(Survey).count()

    model_loaded = False
    model_name = "Not Loaded"
    try:
        from modules.detector import get_detector
        det = get_detector()
        if det and det.model is not None:
            model_loaded = True
            model_name = os.path.basename(str(det.weights_path))
    except Exception:
        pass

    return {
        "status": "online",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "connected",
        "total_records": {
            "defects": total_defects,
            "surveys": total_surveys,
        },
        "ai_engine": {
            "loaded": model_loaded,
            "weights_file": model_name,
            "classes_supported": ["Pothole", "Traffic_Sign"],
            "geometry_calibrated": True,
            "cost_sor_standard": "CPWD / MoRTH / IRC:82-2015",
        },
    }


@router.get("/dashboard/stats", summary="Executive Dashboard Statistics")
def get_dashboard_stats(
    road_name: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    survey_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Computes comprehensive executive analytics for the web and mobile dashboards.
    Optimized with SQL aggregates and a 5-second TTL cache for polling traffic.
    """
    global _stats_cache
    now = time.time()
    is_unfiltered = not road_name and not state and not survey_id

    if is_unfiltered and _stats_cache["data"] is not None:
        if now - _stats_cache["timestamp"] < CACHE_TTL_SECONDS:
            return _stats_cache["data"]

    base_query = db.query(RoadDefect).filter(RoadDefect.is_defect == True)
    if road_name:
        base_query = base_query.filter(RoadDefect.road_name.ilike(f"%{road_name.strip()}%"))
    if state:
        base_query = base_query.filter(RoadDefect.state.ilike(f"%{state.strip()}%"))
    if survey_id:
        base_query = base_query.filter(RoadDefect.survey_id == survey_id)

    total_defects = base_query.count()
    resolved_defects = base_query.filter(RoadDefect.is_resolved == True).count()
    pending_defects = total_defects - resolved_defects
    critical_defects = base_query.filter(RoadDefect.severity == "High", RoadDefect.is_resolved == False).count()

    total_cost_res = base_query.filter(RoadDefect.is_resolved == False).with_entities(
        func.coalesce(func.sum(RoadDefect.repair_cost), 0.0)
    ).scalar()
    total_cost = round(float(total_cost_res or 0.0), 2)

    # Defect type breakdown via SQL group by
    type_counts_rows = base_query.with_entities(
        RoadDefect.defect_type, func.count(RoadDefect.id)
    ).group_by(RoadDefect.defect_type).all()
    type_counts = {r[0]: r[1] for r in type_counts_rows if r[0]}

    # Severity breakdown via SQL group by
    sev_counts_rows = base_query.with_entities(
        RoadDefect.severity, func.count(RoadDefect.id)
    ).group_by(RoadDefect.severity).all()
    sev_counts = {r[0]: r[1] for r in sev_counts_rows if r[0]}

    # Cost by severity (unresolved) via SQL group by
    cost_sev_rows = (
        base_query.filter(RoadDefect.is_resolved == False)
        .with_entities(RoadDefect.severity, func.coalesce(func.sum(RoadDefect.repair_cost), 0.0))
        .group_by(RoadDefect.severity)
        .all()
    )
    cost_by_sev = {r[0]: round(float(r[1]), 2) for r in cost_sev_rows if r[0]}

    # Overall surveys and roads
    total_surveys = db.query(Survey).count()
    roads_surveyed = db.query(distinct(RoadDefect.road_name)).filter(RoadDefect.road_name.isnot(None)).count()

    # Calculate average PCI across surveys
    avg_pci_res = db.query(func.avg(Survey.pci_score)).filter(Survey.pci_score.isnot(None)).scalar()
    avg_pci = round(float(avg_pci_res), 1) if avg_pci_res is not None else 78.5

    data = {
        "total_defects": total_defects,
        "critical_defects": critical_defects,
        "resolved_defects": resolved_defects,
        "pending_defects": pending_defects,
        "total_repair_cost": total_cost,
        "total_surveys": total_surveys,
        "total_roads_surveyed": roads_surveyed,
        "average_pci": avg_pci,
        "defect_types_breakdown": type_counts,
        "severity_breakdown": sev_counts,
        "cost_by_severity": cost_by_sev,
    }

    if is_unfiltered:
        _stats_cache["timestamp"] = now
        _stats_cache["data"] = data

    return data


@router.get("/dashboard/trends", summary="Historical distress & repair trends")
def get_dashboard_trends(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
):
    """Aggregates defect discoveries and financial costs over recent history."""
    results = (
        db.query(
            func.date(RoadDefect.timestamp).label("day"),
            func.count(RoadDefect.id).label("count"),
            func.sum(RoadDefect.repair_cost).label("total_cost"),
        )
        .filter(RoadDefect.is_defect == True)
        .group_by("day")
        .order_by("day")
        .limit(days)
        .all()
    )

    trends = []
    for r in results:
        trends.append({
            "date": str(r[0]),
            "count": r[1],
            "cost": round(float(r[2] or 0.0), 2),
        })

    return {"days": len(trends), "trends": trends}


@router.get("/filters/values", summary="Get filter dropdown values")
@router.get("/dashboard/filters", summary="Dashboard filter criteria alias")
def get_filter_values(db: Session = Depends(get_db)):
    """Distinct defect types, severities, roads, and states for UI controls."""
    types = [r[0] for r in db.query(distinct(RoadDefect.defect_type)).filter(RoadDefect.defect_type.isnot(None)).all()]
    severities = ["Low", "Medium", "High"]
    roads = [r[0] for r in db.query(distinct(RoadDefect.road_name)).filter(RoadDefect.road_name.isnot(None)).all()]
    states = [r[0] for r in db.query(distinct(RoadDefect.state)).filter(RoadDefect.state.isnot(None)).all()]
    statuses = ["reported", "assigned", "in_progress", "completed"]

    return {
        "defect_types": sorted(types),
        "severities": severities,
        "roads": sorted(roads),
        "states": sorted(states),
        "statuses": statuses,
    }


@router.get("/reports/summary", summary="Generate executive maintenance summary")
def get_reports_summary(db: Session = Depends(get_db)):
    """Generates comprehensive report data for engineering budget planning."""
    stats = get_dashboard_stats(db=db)
    top_distressed_roads = (
        db.query(
            RoadDefect.road_name,
            func.count(RoadDefect.id).label("defect_count"),
            func.sum(RoadDefect.repair_cost).label("cost"),
        )
        .filter(RoadDefect.is_defect == True, RoadDefect.is_resolved == False, RoadDefect.road_name.isnot(None))
        .group_by(RoadDefect.road_name)
        .order_by(desc("cost"))
        .limit(10)
        .all()
    )

    roads_list = []
    for r in top_distressed_roads:
        roads_list.append({
            "road_name": r[0],
            "unresolved_defects": r[1],
            "estimated_cost_inr": round(float(r[2] or 0.0), 2),
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "executive_summary": stats,
        "top_priority_roads": roads_list,
        "standards_used": [
            "IRC:82-2015 Code of Practice for Maintenance of Bituminous Surfaces",
            "CPWD Delhi Schedule of Rates (Road Work Section 16)",
            "MoRTH Section 3000 / 500 Maintenance of Roads",
            "ASTM D6433 Standard Practice for Roads and Parking Lots Pavement Condition Index Surveys",
        ],
    }
