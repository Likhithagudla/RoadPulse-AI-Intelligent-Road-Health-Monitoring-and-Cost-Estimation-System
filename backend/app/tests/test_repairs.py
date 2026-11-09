"""
RoadPulse AI - Repairs Workflow Tests
Verifies repair submission, administrative approval, and automatic defect resolution.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.defect import RoadDefect


def test_repair_lifecycle_and_defect_resolution(
    client: TestClient,
    worker_token: str,
    admin_token: str,
    db_session: Session,
):
    """
    Tests complete repair lifecycle:
    1. Defects exist on a road.
    2. Worker submits repair record.
    3. Admin approves repair.
    4. Defects on that road are automatically marked is_resolved=True.
    """
    # 1. Seed unresolved defects on "Grand Trunk Road"
    d1 = RoadDefect(
        road_name="Grand Trunk Road",
        defect_type="Pothole",
        severity="High",
        confidence=0.92,
        repair_cost=1500.0,
        is_defect=True,
        is_resolved=False,
    )
    d2 = RoadDefect(
        road_name="Grand Trunk Road",
        defect_type="Pothole",
        severity="Medium",
        confidence=0.88,
        repair_cost=800.0,
        is_defect=True,
        is_resolved=False,
    )
    db_session.add_all([d1, d2])
    db_session.commit()

    # 2. Worker submits repair
    repair_payload = {
        "road_name": "Grand Trunk Road",
        "surveyor_name": "worker1",
        "admin_notes": "Patched with hot mix asphalt",
    }
    submit_res = client.post(
        "/api/repairs",
        json=repair_payload,
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert submit_res.status_code == 201
    repair_id = submit_res.json()["id"]
    assert submit_res.json()["status"] == "pending"

    # 3. Admin approves repair
    approve_res = client.patch(
        f"/api/repairs/{repair_id}/approve",
        json={"admin_notes": "Inspected and verified quality"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_res.status_code == 200
    appr_data = approve_res.json()
    assert appr_data["status"] == "approved"
    assert appr_data["defects_resolved"] == 2
    assert appr_data["cost_saved"] == 2300.0

    # 4. Verify defects in database are resolved
    db_session.refresh(d1)
    db_session.refresh(d2)
    assert d1.is_resolved is True
    assert d2.is_resolved is True
    assert d1.status == "completed"
    assert d2.status == "completed"
