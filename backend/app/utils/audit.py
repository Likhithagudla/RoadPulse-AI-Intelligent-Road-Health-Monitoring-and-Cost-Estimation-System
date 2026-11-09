"""
RoadPulse AI - Audit Logging Utility
Provides helper functions for recording immutable system actions and security events.
"""

from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from fastapi import Request

from ..models.audit_log import AuditLog


def log_audit_event(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """Creates and persists an audit log record."""
    ip_addr = None
    if request:
        client = getattr(request, "client", None)
        if client:
            ip_addr = getattr(client, "host", None)

    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_addr,
    )
    try:
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        # Non-blocking failure: print warning but do not crash the core transaction
        print(f"[AUDIT WARN] Failed writing audit log: {e}")
    return audit_entry
