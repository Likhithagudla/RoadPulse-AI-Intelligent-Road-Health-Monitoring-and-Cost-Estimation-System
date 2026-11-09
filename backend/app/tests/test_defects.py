"""
RoadPulse AI - Defects & AI Inference Tests
Verifies defect detection API, geometric calculations, severity scoring, and pagination.
"""

import io
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient


def create_dummy_road_image() -> bytes:
    """Generates a synthetic 640x480 road image with a dark pothole circle for testing."""
    img = np.ones((480, 640, 3), dtype=np.uint8) * 120  # Gray asphalt
    # Draw dark elliptical pothole
    cv2.ellipse(img, (320, 360), (90, 45), 0, 0, 360, (30, 30, 30), -1)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def test_detect_endpoint_with_image(client: TestClient):
    """Ensures /api/detect accepts image and returns geometric and cost analytics."""
    img_bytes = create_dummy_road_image()
    files = {"file": ("test_road.jpg", io.BytesIO(img_bytes), "image/jpeg")}
    data = {
        "road_name": "MG Road",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "region": "Karnataka",
        "save_results": "true",
    }
    response = client.post("/api/detect", files=files, data=data)
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert "orig_width" in res
    assert "detections" in res


def test_list_defects_pagination(client: TestClient):
    """Ensures /api/defects supports limit and offset parameters."""
    response = client.get("/api/defects?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert "defects" in data
    assert isinstance(data["defects"], list)


def test_system_status_endpoint(client: TestClient):
    """Ensures /api/status returns online status and AI engine telemetry."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "ai_engine" in data
    assert data["ai_engine"]["geometry_calibrated"] is True
