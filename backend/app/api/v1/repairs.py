"""
RoadPulse AI - Repair Workflows Router
Tracks field repairs with strict administrative approval gates.
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ...core.database import get_db
from ...core.dependencies import require_admin, require_worker_or_admin
from ...models.user import User
from ...models.repair import RepairRecord
from ...models.defect import RoadDefect
from ...schemas.repair import (
    RepairCreate,
    RepairApproval,
    RepairResponse,
    RepairListResponse,
)
from ...utils.pagination import pagination_params

router = APIRouter(prefix="/repairs", tags=["Repairs"])


@router.post("", response_model=RepairResponse, status_code=status.HTTP_201_CREATED, summary="Submit repair record")
def submit_repair(
    repair_in: RepairCreate,
    current_user: User = Depends(require_worker_or_admin),
    db: Session = Depends(get_db),
):
    """Submits completed patch repair for administrative review."""
    new_repair = RepairRecord(
        road_name=repair_in.road_name.strip(),
        survey_id=repair_in.survey_id,
        surveyor_name=repair_in.surveyor_name or current_user.username,
        admin_notes=repair_in.admin_notes,
        status=repair_in.status if repair_in.status in ("pending", "approved", "rejected") else "pending",
        defects_resolved=repair_in.defects_resolved or 0,
        cost_saved=repair_in.cost_saved or 0.0,
    )
    db.add(new_repair)
    db.commit()
    db.refresh(new_repair)
    return new_repair


@router.get("", response_model=RepairListResponse, summary="List repairs (paginated)")
def list_repairs(
    status: Optional[str] = Query(None),
    road_name: Optional[str] = Query(None),
    pagination: tuple = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    """Retrieves repair verification records."""
    limit, offset = pagination
    query = db.query(RepairRecord)
    if status:
        query = query.filter(RepairRecord.status == status.strip())
    if road_name:
        query = query.filter(RepairRecord.road_name.ilike(f"%{road_name.strip()}%"))

    total = query.count()
    repairs = query.order_by(desc(RepairRecord.created_at)).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "repairs": repairs,
    }


@router.patch("/{repair_id}/approve", response_model=RepairResponse, summary="Approve road repair")
def approve_repair(
    repair_id: int,
    approval_in: Optional[RepairApproval] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Administrative approval for road repairs.
    Atomically resolves related road defects and records public cost savings.
    STRICTLY RESTRICTED TO ADMINS.
    """
    repair = db.query(RepairRecord).filter(RepairRecord.id == repair_id).first()
    if not repair:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repair with ID {repair_id} not found.")

    if repair.status == "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repair is already approved.")

    # Find unresolved defects on this road
    defects_query = db.query(RoadDefect).filter(
        RoadDefect.road_name.ilike(repair.road_name),
        RoadDefect.is_defect == True,
        RoadDefect.is_resolved == False,
    )
    if repair.survey_id:
        defects_query = defects_query.filter(RoadDefect.survey_id == repair.survey_id)

    unresolved_defects = defects_query.all()
    resolved_count = len(unresolved_defects)
    cost_saved = sum(d.repair_cost for d in unresolved_defects)

    now = datetime.now(timezone.utc)
    for d in unresolved_defects:
        d.is_resolved = True
        d.resolved_at = now
        d.status = "completed"

    repair.status = "approved"
    repair.defects_resolved = resolved_count
    repair.cost_saved = round(cost_saved, 2)
    if approval_in and approval_in.admin_notes:
        repair.admin_notes = approval_in.admin_notes

    db.commit()
    db.refresh(repair)

    return repair


@router.patch("/{repair_id}/reject", response_model=RepairResponse, summary="Reject road repair")
def reject_repair(
    repair_id: int,
    rejection_in: Optional[RepairApproval] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Rejects repair verification. Strictly restricted to Admins."""
    repair = db.query(RepairRecord).filter(RepairRecord.id == repair_id).first()
    if not repair:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repair with ID {repair_id} not found.")

    repair.status = "rejected"
    if rejection_in and rejection_in.admin_notes:
        repair.admin_notes = rejection_in.admin_notes

    db.commit()
    db.refresh(repair)
    return repair
