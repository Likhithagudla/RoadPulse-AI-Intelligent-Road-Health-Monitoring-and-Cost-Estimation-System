"""
RoadPulse AI - Admin Management & Audit Trail Integration Tests
Verifies user management, account activation toggle, and audit log generation.
"""

from fastapi.testclient import TestClient

def test_admin_list_users_and_toggle_active(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Query users
    res = client.get("/api/admin/users", headers=headers)
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 2

    # Find worker or citizen user
    non_admin = next((u for u in users if u["role"] != "admin"), None)
    assert non_admin is not None

    # 2. Toggle active status
    toggle_res = client.patch(
        f"/api/admin/users/{non_admin['id']}/toggle-active",
        headers=headers,
    )
    assert toggle_res.status_code == 200
    updated_user = toggle_res.json()
    assert updated_user["is_active"] != non_admin["is_active"]

    # Toggle back to original
    toggle_back = client.patch(
        f"/api/admin/users/{non_admin['id']}/toggle-active",
        headers=headers,
    )
    assert toggle_back.status_code == 200
    assert toggle_back.json()["is_active"] == non_admin["is_active"]


def test_admin_cannot_deactivate_self(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Retrieve current admin profile
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    admin_id = me_res.json()["id"]

    # Attempt to deactivate self
    deact_res = client.patch(
        f"/api/admin/users/{admin_id}/toggle-active",
        headers=headers,
    )
    assert deact_res.status_code == 400
    assert "cannot deactivate their own account" in deact_res.json()["detail"].lower()


def test_audit_logs_retrieval(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/admin/audit-logs", headers=headers)
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)


def test_dashboard_trends_endpoint(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/dashboard/trends?days=14", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "trends" in data
    assert isinstance(data["trends"], list)
