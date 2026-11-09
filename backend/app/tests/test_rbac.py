"""
RoadPulse AI - Role-Based Access Control (RBAC) Tests
Verifies strict endpoint protection for Admin, Worker, and User roles.
"""

import pytest
from fastapi.testclient import TestClient


def test_unauthenticated_request_rejected(client: TestClient):
    """Ensures protected endpoints reject requests without token with 401."""
    response = client.post("/api/roads", json={"road_id": "NH-1", "road_name": "Test NH"})
    assert response.status_code == 401


def test_citizen_cannot_create_road(client: TestClient, user_token: str):
    """Ensures standard user cannot create road master records (403 Forbidden)."""
    response = client.post(
        "/api/roads",
        json={"road_id": "NH-99", "road_name": "Unauthorized Highway"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_admin_can_create_road(client: TestClient, admin_token: str):
    """Ensures administrator can create road master records."""
    response = client.post(
        "/api/roads",
        json={"road_id": "NH-48", "road_name": "Delhi Mumbai Expressway", "state": "Maharashtra"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["road_id"] == "NH-48"


def test_citizen_cannot_approve_repairs(client: TestClient, user_token: str):
    """Ensures citizen cannot approve repairs (403 Forbidden)."""
    response = client.patch(
        "/api/repairs/1/approve",
        json={"admin_notes": "Fake approval"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_worker_cannot_approve_repairs(client: TestClient, worker_token: str):
    """Ensures field worker cannot approve their own or any repairs (403 Forbidden)."""
    response = client.patch(
        "/api/repairs/1/approve",
        json={"admin_notes": "Self approval"},
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert response.status_code == 403
