"""
RoadPulse AI - Worker & User Tasks Router
Task execution for field repair personnel and user reporting history.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ...core.database import get_db
from ...core.dependencies import require_role, get_current_user
from ...models.user import User
from ...models.defect import RoadDefect
from ...models.work_order import WorkOrder
from ...schemas.defect import StatusUpdate, DefectResponse

router = APIRouter(tags=["Worker & User Tasks"])


@router.get("/worker/tasks", summary="List worker assigned tasks")
def get_worker_tasks(
    current_worker: User = Depends(require_role(["worker", "admin"])),
    db: Session = Depends(get_db),
):
    """Returns repair assignments dispatched to the current worker."""
    orders = (
        db.query(WorkOrder)
        .filter(WorkOrder.assigned_to == current_worker.id)
        .order_by(desc(WorkOrder.created_at))
        .all()
    )

    tasks = []
    for order in orders:
        defect = order.issue
        if not defect:
            continue
        tasks.append({
            "task_id": order.id,
            "issue_id": defect.id,
            "status": order.status,
            "admin_notes": order.admin_notes,
            "worker_notes": order.worker_notes,
            "defect_type": defect.defect_type,
            "severity": defect.severity,
            "road_name": defect.road_name,
            "latitude": defect.latitude,
            "longitude": defect.longitude,
            "estimated_area_sqm": defect.estimated_area_sqm,
            "repair_cost": defect.repair_cost,
            "repair_description": defect.repair_description,
            "image_path": defect.image_path,
            "annotated_image_path": defect.annotated_image_path,
            "created_at": order.created_at,
        })

    return {"total_tasks": len(tasks), "tasks": tasks}


@router.post("/worker/update-status", summary="Update task progress")
def update_task_status(
    status_in: StatusUpdate,
    current_worker: User = Depends(require_role(["worker", "admin"])),
    db: Session = Depends(get_db),
):
    """Updates work order and defect execution progress (assigned -> in_progress -> completed)."""
    defect = db.query(RoadDefect).filter(RoadDefect.id == status_in.issue_id).first()
    if not defect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Defect {status_in.issue_id} not found.")

    # Ownership check: Ensure worker is assigned to this issue (or is admin)
    if current_worker.role != "admin" and defect.assigned_to != current_worker.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to work on this road distress issue.",
        )

    # Validate state transitions
    valid_states = ("assigned", "in_progress", "completed")
    if status_in.status not in valid_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{status_in.status}'. Allowed: {valid_states}",
        )

    defect.status = status_in.status
    if status_in.status == "completed":
        defect.is_resolved = True
        defect.resolved_at = datetime.now(timezone.utc)

    order = db.query(WorkOrder).filter(WorkOrder.issue_id == defect.id).first()
    if order:
        order.status = status_in.status
        if status_in.notes:
            order.worker_notes = status_in.notes

    db.commit()

    return {
        "success": True,
        "message": f"Status updated to '{status_in.status}'.",
        "issue_id": defect.id,
    }


@router.get("/user/my-reports", response_model=List[DefectResponse], summary="Citizen defect reports history")
def get_user_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns defect reports submitted by the authenticated citizen/user."""
    return (
        db.query(RoadDefect)
        .filter(RoadDefect.reported_by == current_user.id)
        .order_by(desc(RoadDefect.timestamp))
        .all()
    )
