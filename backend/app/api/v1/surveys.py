"""
RoadPulse AI - Road Surveys Router
CRUD and life-cycle management for inspection survey drives.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ...core.database import get_db
from ...core.dependencies import require_worker_or_admin, get_current_user
from ...models.user import User
from ...models.survey import Survey
from ...models.defect import RoadDefect
from ...schemas.survey import (
    SurveyCreate,
    SurveyStatusUpdate,
    SurveyResponse,
    SurveyListResponse,
)
from ...utils.pagination import pagination_params

router = APIRouter(prefix="/surveys", tags=["Surveys"])


@router.post("", response_model=SurveyResponse, status_code=status.HTTP_201_CREATED, summary="Create a road survey")
def create_survey(
    survey_in: SurveyCreate,
    current_user: User = Depends(require_worker_or_admin),
    db: Session = Depends(get_db),
):
    """Initializes a new road inspection survey drive. Restricted to Workers and Admins."""
    total_length = max(0.0, survey_in.end_chainage - survey_in.start_chainage) / 1000.0

    new_survey = Survey(
        road_name=survey_in.road_name.strip(),
        road_id=survey_in.road_id.strip() if survey_in.road_id else None,
        road_type=survey_in.road_type,
        state=survey_in.state,
        start_chainage=survey_in.start_chainage,
        end_chainage=survey_in.end_chainage,
        total_length_km=total_length,
        start_latitude=survey_in.start_latitude,
        start_longitude=survey_in.start_longitude,
        surveyor_name=survey_in.surveyor_name or current_user.username,
        vehicle_id=survey_in.vehicle_id,
        status="pending",
    )
    db.add(new_survey)
    db.commit()
    db.refresh(new_survey)

    return new_survey


@router.get("", response_model=SurveyListResponse, summary="List road surveys (paginated)")
def list_surveys(
    road_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    pagination: tuple = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    """
    Retrieves surveys with pagination.
    Solves N+1 queries by executing aggregated SQL joins for defect counts and repair costs.
    """
    limit, offset = pagination

    # Base query with aggregated defect statistics
    query = (
        db.query(
            Survey,
            func.count(RoadDefect.id).label("defect_count"),
            func.coalesce(func.sum(RoadDefect.repair_cost), 0.0).label("total_cost"),
        )
        .outerjoin(RoadDefect, RoadDefect.survey_id == Survey.id)
        .group_by(Survey.id)
    )

    if road_name:
        query = query.filter(Survey.road_name.ilike(f"%{road_name.strip()}%"))
    if status:
        query = query.filter(Survey.status == status.strip())
    if state:
        query = query.filter(Survey.state.ilike(f"%{state.strip()}%"))

    total = query.count()
    results = query.order_by(desc(Survey.survey_date)).offset(offset).limit(limit).all()

    survey_responses = []
    for survey_obj, defect_cnt, total_cost in results:
        # Dynamically sync calculated totals
        survey_obj.total_defects = defect_cnt
        survey_obj.total_repair_cost = round(float(total_cost), 2)
        survey_responses.append(survey_obj)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "surveys": survey_responses,
    }


@router.get("/{survey_id}", summary="Get detailed survey results")
def get_survey(
    survey_id: int,
    db: Session = Depends(get_db),
):
    """Retrieves survey metadata along with all associated defects and condition metrics."""
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Survey with ID {survey_id} not found.")

    defects = db.query(RoadDefect).filter(RoadDefect.survey_id == survey_id).order_by(RoadDefect.chainage).all()

    return {
        "survey": survey,
        "total_defects": len(defects),
        "total_repair_cost": sum(d.repair_cost for d in defects),
        "defects": defects,
    }


@router.patch("/{survey_id}/status", response_model=SurveyResponse, summary="Update survey processing status")
def update_survey_status(
    survey_id: int,
    update_in: SurveyStatusUpdate,
    current_user: User = Depends(require_worker_or_admin),
    db: Session = Depends(get_db),
):
    """Updates survey lifecycle state (pending, processing, completed, failed). Restricted to Workers & Admins."""
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Survey with ID {survey_id} not found.")

    survey.status = update_in.status
    db.commit()
    db.refresh(survey)
    return survey
