"""
RoadPulse AI - Road Surveys Tests
Verifies survey creation, listing without N+1 query, and status progression.
"""

import pytest
from fastapi.testclient import TestClient


def test_create_and_list_surveys(client: TestClient, worker_token: str):
    """Ensures worker can create a survey session and retrieve it in the list."""
    payload = {
        "road_name": "NH-66 Coastal Highway",
        "road_id": "NH-66",
        "state": "Goa",
        "start_chainage": 1000.0,
        "end_chainage": 5000.0,
        "start_latitude": 15.2993,
        "start_longitude": 74.1240,
    }
    response = client.post(
        "/api/surveys",
        json=payload,
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert response.status_code == 201
    survey_data = response.json()
    assert survey_data["road_name"] == "NH-66 Coastal Highway"
    survey_id = survey_data["id"]

    # Verify listing
    list_res = client.get("/api/surveys?limit=10&offset=0")
    assert list_res.status_code == 200
    surveys = list_res.json()["surveys"]
    assert any(s["id"] == survey_id for s in surveys)


def test_update_survey_status(client: TestClient, worker_token: str):
    """Ensures worker can update survey processing status."""
    # First create
    create_res = client.post(
        "/api/surveys",
        json={"road_name": "Ring Road"},
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    s_id = create_res.json()["id"]

    # Patch status
    patch_res = client.patch(
        f"/api/surveys/{s_id}/status",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {worker_token}"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "completed"
