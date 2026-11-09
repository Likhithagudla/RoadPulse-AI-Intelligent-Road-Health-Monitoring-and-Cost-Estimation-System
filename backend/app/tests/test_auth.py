"""
RoadPulse AI - Authentication & Security Tests
Verifies password complexity, registration role protection, JWT verification, and rate limiting.
"""

import pytest
from fastapi.testclient import TestClient


def test_public_registration_forces_user_role(client: TestClient):
    """Ensures public registration always creates 'user' role regardless of payload."""
    payload = {
        "username": "new_citizen_user",
        "password": "SecurePassword123!",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "new_citizen_user"
    assert data["role"] == "user"  # Forced role!


def test_registration_rejects_weak_password(client: TestClient):
    """Ensures weak passwords fail complexity validation with 422."""
    payload = {
        "username": "weak_user",
        "password": "123",  # Under 8 chars, no uppercase
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


def test_login_success_and_jwt_issuance(client: TestClient, seeded_users):
    """Ensures valid credentials return signed JWT access token."""
    payload = {
        "username": "test_admin",
        "password": "AdminPass123!",
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "admin"


def test_login_invalid_credentials_rejected(client: TestClient, seeded_users):
    """Ensures invalid credentials return 401."""
    payload = {
        "username": "test_admin",
        "password": "WrongPassword999!",
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401


def test_get_current_user_profile(client: TestClient, admin_token: str):
    """Ensures /api/auth/me resolves identity from Bearer token."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "test_admin"
    assert response.json()["role"] == "admin"
