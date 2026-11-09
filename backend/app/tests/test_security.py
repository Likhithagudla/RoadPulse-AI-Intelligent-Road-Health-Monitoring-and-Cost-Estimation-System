"""
RoadPulse AI - Security & Penetration Testing Suite
Tests security boundaries and attack vectors:
- Privilege escalation prevention (forced citizen role on registration)
- Role-based authorization enforcement across administrative endpoints
- JWT tampering, invalid signatures, malformed headers, and token expiration
- Malformed and malicious file uploads (0-byte files, non-image files, corrupted buffers)
- SQL injection resistance on query parameters
- Cross-Site Scripting (XSS) payload handling
"""

import io
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient

from app.core.security import SecurityService


# ==========================================
# 1. PRIVILEGE ESCALATION ATTEMPTS
# ==========================================

def test_privilege_escalation_via_registration_payload(client: TestClient):
    """
    Ensures public registration ignores any client-supplied 'role' field.
    An attacker sending {"role": "admin"} or {"role": "worker"} must strictly receive role='user'.
    """
    malicious_payload = {
        "username": "attacker_trying_admin",
        "password": "AttackerPass123!",
        "role": "admin",
        "is_active": True,
    }
    response = client.post("/api/auth/register", json=malicious_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "attacker_trying_admin"
    assert data["role"] == "user"  # Explicitly forced to 'user'!


def test_privilege_escalation_worker_cannot_access_admin_api(client: TestClient, worker_token: str):
    """Ensures worker accounts cannot access /api/admin endpoints."""
    headers = {"Authorization": f"Bearer {worker_token}"}
    
    # List users
    res = client.get("/api/admin/users", headers=headers)
    assert res.status_code == 403

    # List audit logs
    res_audit = client.get("/api/admin/audit-logs", headers=headers)
    assert res_audit.status_code == 403

    # Toggle active
    res_toggle = client.patch("/api/admin/users/1/toggle-active", headers=headers)
    assert res_toggle.status_code == 403


def test_citizen_cannot_access_worker_endpoints(client: TestClient, user_token: str):
    """Ensures standard citizen cannot submit official repair records or surveys."""
    headers = {"Authorization": f"Bearer {user_token}"}

    # Cannot create survey
    res_survey = client.post(
        "/api/surveys",
        json={"road_name": "Unauthorized Survey"},
        headers=headers,
    )
    assert res_survey.status_code == 403

    # Cannot approve repairs
    res_repair = client.patch(
        "/api/repairs/1/approve",
        json={"admin_notes": "Citizen approve"},
        headers=headers,
    )
    assert res_repair.status_code == 403


# ==========================================
# 2. JWT TOKEN SECURITY & EXPIRATION
# ==========================================

def test_tampered_jwt_signature_rejected(client: TestClient, user_token: str):
    """Ensures modifying token payload without valid signature returns 401."""
    # Split token into header.payload.signature
    parts = user_token.split(".")
    # Tamper payload part
    tampered_token = f"{parts[0]}.eyJhZG1pbiI6dHJ1ZX0.{parts[2]}"
    
    res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert res.status_code == 401
    assert "invalid" in res.json()["detail"].lower()


def test_malformed_jwt_token_rejected(client: TestClient):
    """Ensures arbitrary non-JWT strings in Authorization header return 401."""
    res = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-real-jwt-token-string"},
    )
    assert res.status_code == 401


def test_missing_or_bad_authorization_header(client: TestClient):
    """Ensures missing 'Bearer ' prefix or empty authorization returns 401."""
    res = client.get(
        "/api/auth/me",
        headers={"Authorization": "Basic some_credentials"},
    )
    assert res.status_code == 401


def test_expired_jwt_token_rejected(client: TestClient):
    """Ensures an expired JWT token is rejected with 401."""
    expired_token = SecurityService.create_access_token(
        data={"sub": "test_user", "role": "user"},
        expires_delta=timedelta(minutes=-10),  # Expired 10 minutes ago
    )
    res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower() or "invalid" in res.json()["detail"].lower()


# ==========================================
# 3. MALFORMED FILE UPLOADS
# ==========================================

def test_upload_zero_byte_file_rejected(client: TestClient):
    """Ensures empty 0-byte file upload to /api/detect returns 400 Bad Request."""
    files = {"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}
    response = client.post("/api/detect", files=files)
    assert response.status_code in (400, 422)
    assert "empty" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()


def test_upload_corrupted_image_bytes_rejected(client: TestClient):
    """Ensures non-image bytes named .jpg return 400 without crashing."""
    corrupted_bytes = b"THIS_IS_NOT_A_VALID_JPEG_OR_PNG_IMAGE_FILE"
    files = {"file": ("corrupt.jpg", io.BytesIO(corrupted_bytes), "image/jpeg")}
    response = client.post("/api/detect", files=files)
    assert response.status_code in (400, 422)
    assert "corrupt" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()


def test_upload_unsupported_file_extension(client: TestClient):
    """Ensures non-image files (.exe, .sh, .txt) are rejected with 400."""
    files = {"file": ("exploit.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")}
    response = client.post("/api/detect", files=files)
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower() or "image" in response.json()["detail"].lower()


# ==========================================
# 4. INPUT VALIDATION & INJECTION RESISTANCE
# ==========================================

def test_sql_injection_in_defects_query_params(client: TestClient):
    """Ensures SQL injection strings in query parameters are escaped by SQLAlchemy."""
    sqli_payload = "' OR '1'='1' --"
    response = client.get(f"/api/defects?road_name={sqli_payload}")
    assert response.status_code == 200
    data = response.json()
    assert "defects" in data
    assert isinstance(data["defects"], list)
    # The literal search should return 0 results unless a road is named "' OR '1'='1' --"
    assert data["total"] == 0


def test_xss_payload_in_defect_road_name_handled_safely(client: TestClient, admin_token: str):
    """Ensures Cross-Site Scripting (XSS) strings are stored as text without crashing or injection."""
    xss_name = "<script>alert('XSS_ATTACK')</script>"
    res = client.post(
        "/api/roads",
        json={"road_id": "XSS-ROAD-1", "road_name": xss_name},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    assert res.json()["road_name"] == xss_name
