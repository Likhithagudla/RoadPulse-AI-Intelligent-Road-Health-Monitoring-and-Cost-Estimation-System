"""
RoadPulse AI - Administrator Router
Admin operations: work dispatch, worker management, and system governance.
All endpoints are strictly protected by role-based access control (Admin role only).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ...core.database import get_db
from ...core.dependencies import require_admin
from ...core.security import SecurityService
from ...models.user import User
from ...models.defect import RoadDefect
from ...models.work_order import WorkOrder
from ...schemas.user import UserCreateAdmin, UserResponse
from ...schemas.defect import WorkAssignment, DefectResponse

router = APIRouter(prefix="/admin", tags=["Administration"], dependencies=[Depends(require_admin)])


@router.get("/issues", response_model=List[DefectResponse], summary="Admin issues management")
def get_admin_issues(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Returns issues view with assigned worker context for dispatching."""
    query = db.query(RoadDefect).filter(RoadDefect.is_defect == True)
    if status:
        query = query.filter(RoadDefect.status == status.strip())
    return query.order_by(desc(RoadDefect.timestamp)).all()


@router.post("/assign-work", summary="Dispatch work order to a field worker")
@router.post("/assign", summary="Dispatch work order to a field worker (alias)")
def assign_work(
    assignment: WorkAssignment,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Assigns defect repair task to a qualified worker."""
    defect = db.query(RoadDefect).filter(RoadDefect.id == assignment.issue_id).first()
    if not defect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Defect {assignment.issue_id} not found.")

    worker = db.query(User).filter(User.id == assignment.worker_id, User.role == "worker").first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Worker with ID {assignment.worker_id} not found or user does not have the 'worker' role.",
        )

    # Check for existing work order
    order = db.query(WorkOrder).filter(WorkOrder.issue_id == defect.id).first()
    if order:
        order.assigned_to = worker.id
        order.status = "assigned"
        order.admin_notes = assignment.notes
    else:
        order = WorkOrder(
            issue_id=defect.id,
            assigned_to=worker.id,
            status="assigned",
            admin_notes=assignment.notes,
        )
        db.add(order)

    # Update defect status
    defect.assigned_to = worker.id
    defect.status = "assigned"

    db.commit()
    return {
        "success": True,
        "message": f"Defect #{defect.id} assigned to worker '{worker.username}'.",
        "work_order_id": order.id,
    }


@router.get("/workers", response_model=List[UserResponse], summary="List all worker accounts")
def list_workers(db: Session = Depends(get_db)):
    """Returns active field crew accounts."""
    return db.query(User).filter(User.role == "worker", User.is_active == True).all()


@router.get("/analytics", summary="Admin team performance & backlog analytics")
def get_admin_analytics(db: Session = Depends(get_db)):
    """Computes worker efficiency, resolution times, and backlog metrics."""
    total_assigned = db.query(WorkOrder).count()
    completed_orders = db.query(WorkOrder).filter(WorkOrder.status == "completed").count()
    in_progress = db.query(WorkOrder).filter(WorkOrder.status == "in_progress").count()

    # Per worker task load
    worker_loads = (
        db.query(User.username, func.count(WorkOrder.id))
        .join(WorkOrder, WorkOrder.assigned_to == User.id)
        .group_by(User.username)
        .all()
    )

    return {
        "work_orders": {
            "total": total_assigned,
            "completed": completed_orders,
            "in_progress": in_progress,
            "completion_rate_pct": round((completed_orders / max(1, total_assigned)) * 100, 1),
        },
        "worker_task_distribution": {w[0]: w[1] for w in worker_loads},
    }


@router.post("/create-user", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create privileged account")
@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create privileged account (REST alias)")
def admin_create_user(
    user_in: UserCreateAdmin,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Administrator endpoint to safely provision new worker or administrator accounts.
    Enforces password complexity.
    """
    existing = db.query(User).filter(User.username.ilike(user_in.username.strip())).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_in.username}' already exists.",
        )

    valid_pw, pw_err = SecurityService.validate_password_strength(user_in.password)
    if not valid_pw:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=pw_err)

    hashed = SecurityService.get_password_hash(user_in.password)
    new_user = User(
        username=user_in.username.strip(),
        password_hash=hashed,
        role=user_in.role,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/users", response_model=List[UserResponse], summary="List all user accounts")
def list_users(
    role: Optional[str] = Query(None, description="Filter by role: admin, worker, user"),
    search: Optional[str] = Query(None, description="Search by username"),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Administrator endpoint to query all system users without exposing sensitive credentials."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role.strip().lower())
    if search:
        query = query.filter(User.username.ilike(f"%{search.strip()}%"))
    return query.order_by(User.id.desc()).all()


@router.patch("/users/{user_id}/toggle-active", response_model=UserResponse, summary="Toggle user active status")
def toggle_user_active(
    user_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Enables or disables a user account. Cannot disable self."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User #{user_id} not found.")

    if target_user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own account.",
        )

    target_user.is_active = not target_user.is_active
    db.commit()
    db.refresh(target_user)
    return target_user


@router.get("/audit-logs", summary="List system audit logs")
def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Retrieves immutable audit trail for governance, compliance, and activity auditing."""
    from ...models.audit_log import AuditLog
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action.strip().upper())
    logs = query.order_by(AuditLog.id.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "username": l.user.username if l.user else "System",
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "details": l.details,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]

