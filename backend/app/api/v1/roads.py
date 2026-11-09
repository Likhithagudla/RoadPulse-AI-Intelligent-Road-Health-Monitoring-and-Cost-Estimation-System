"""
RoadPulse AI - Road Master Data Router
Official road catalog management.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.dependencies import require_admin
from ...models.user import User
from ...models.road import Road
from ...schemas.road import RoadCreate, RoadResponse, RoadListResponse

router = APIRouter(prefix="/roads", tags=["Roads"])


@router.post("", response_model=RoadResponse, status_code=status.HTTP_201_CREATED, summary="Create road record")
def create_road(
    road_in: RoadCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Registers official road master record. Restricted strictly to Administrators."""
    existing = db.query(Road).filter(Road.road_id == road_in.road_id.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Road with ID '{road_in.road_id}' already exists in registry.",
        )

    new_road = Road(
        road_id=road_in.road_id.strip(),
        road_name=road_in.road_name.strip(),
        road_type=road_in.road_type,
        district=road_in.district,
        state=road_in.state,
        total_length_km=road_in.total_length_km,
        start_latitude=road_in.start_latitude,
        start_longitude=road_in.start_longitude,
        end_latitude=road_in.end_latitude,
        end_longitude=road_in.end_longitude,
    )
    db.add(new_road)
    db.commit()
    db.refresh(new_road)

    return new_road


@router.get("", response_model=RoadListResponse, summary="List all master roads")
def list_roads(
    district: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    road_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Returns official master road catalog."""
    query = db.query(Road)
    if district:
        query = query.filter(Road.district.ilike(f"%{district.strip()}%"))
    if state:
        query = query.filter(Road.state.ilike(f"%{state.strip()}%"))
    if road_type:
        query = query.filter(Road.road_type == road_type.strip())

    roads = query.order_by(Road.road_name).all()
    return {"total": len(roads), "roads": roads}
