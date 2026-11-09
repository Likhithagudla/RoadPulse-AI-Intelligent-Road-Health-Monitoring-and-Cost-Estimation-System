"""
RoadPulse AI - End-to-End Live System Integration Verification
Starts the FastAPI server locally, exercises the full authentication, AI inference,
geometry/severity/cost estimation, database persistence, and dashboard endpoints,
and verifies 100% operational readiness.
"""

import sys
import time
import subprocess
import requests
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def run_e2e_verification():
    print("[E2E] Starting RoadPulse FastAPI Backend Server...")
    log_file = PROJECT_ROOT / "backend_e2e.log"
    log_fp = open(log_file, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m", "uvicorn",
            "backend.app.main:create_app",
            "--factory",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--log-level", "warning",
        ],
        cwd=str(PROJECT_ROOT),
        stdout=log_fp,
        stderr=log_fp,
    )

    try:
        # 1. Wait for server readiness via /health
        ready = False
        for attempt in range(20):
            time.sleep(1)
            try:
                r = requests.get(f"{BASE_URL}/health", timeout=2)
                if r.status_code == 200:
                    ready = True
                    print(f"[E2E] Server ready after {attempt + 1}s: {r.json()}")
                    break
            except Exception:
                continue

        if not ready:
            proc.terminate()
            log_fp.close()
            with open(log_file, "r", encoding="utf-8") as f:
                print("SERVER LOGS:\n", f.read())
            raise RuntimeError("FastAPI server failed to start within 15 seconds.")

        # 2. Test Dashboard Static Files & Swagger Docs
        print("\n--- Testing UI & Documentation Routes ---")
        doc_res = requests.get(f"{BASE_URL}/docs", timeout=5)
        assert doc_res.status_code == 200, f"Expected 200 for /docs, got {doc_res.status_code}"
        print("  [PASS] Swagger UI (/docs) returns HTTP 200 OK")

        dash_res = requests.get(f"{BASE_URL}/dashboard/", timeout=5)
        assert dash_res.status_code == 200, f"Expected 200 for /dashboard/, got {dash_res.status_code}"
        assert "RoadPulse" in dash_res.text or "<!DOCTYPE html>" in dash_res.text
        print("  [PASS] Dashboard Web UI (/dashboard/) returns HTTP 200 OK")

        # 3. Test Authentication (Admin Login & Profile)
        print("\n--- Testing Authentication & RBAC ---")
        login_payload = {
            "username": "admin",
            "password": "AdminPassword123!"
        }
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload, timeout=5)
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        auth_data = login_res.json()
        token = auth_data["access_token"]
        role = auth_data["role"]
        assert role == "admin"
        print(f"  [PASS] Logged in as '{login_payload['username']}' with role '{role}'")

        headers = {"Authorization": f"Bearer {token}"}
        me_res = requests.get(f"{BASE_URL}/api/auth/me", headers=headers, timeout=5)
        assert me_res.status_code == 200
        print(f"  [PASS] Verified JWT token via /api/auth/me: {me_res.json()['username']}")

        # 4. Test AI Detection & Cost Estimation Endpoint (/api/detect)
        print("\n--- Testing AI Defect Detection & Cost Estimation Pipeline ---")
        sample_img = PROJECT_ROOT / "ai_models" / "dataset" / "unified" / "images" / "test" / "pot_seg_000008.jpg"
        assert sample_img.exists(), f"Sample image not found: {sample_img}"

        with open(sample_img, "rb") as f:
            files = {"file": ("pot_seg_000008.jpg", f, "image/jpeg")}
            data = {
                "road_name": "NH-48 Pune Highway",
                "state": "Maharashtra",
                "region": "Maharashtra",
                "chainage": 12.5,
                "latitude": 18.5204,
                "longitude": 73.8567,
            }
            detect_res = requests.post(f"{BASE_URL}/api/detect", files=files, data=data, headers=headers, timeout=20)

        assert detect_res.status_code == 200, f"Detect failed: {detect_res.text}"
        det_data = detect_res.json()
        print(f"  [PASS] Image processed successfully.")
        print(f"         Defects Detected: {det_data['total_detections']}")
        print(f"         Total Repair Cost: Rs. {det_data['estimated_total_cost']:,.2f}")
        print(f"         Annotated Overlay: {det_data['annotated_image_url']}")

        if det_data["total_detections"] > 0:
            first_def = det_data["detections"][0]
            print(f"         Defect Type: {first_def['class_name']}")
            print(f"         Physical Severity: {first_def['severity']}")
            print(f"         Calibrated Area: {first_def['estimated_area_sqm']:.4f} m^2")
            print(f"         Cost Breakdown: {first_def.get('detailed_cost_breakdown', {})}")

        # 5. Verify Defect Persistence & Pagination (/api/defects)
        print("\n--- Testing Defect Persistence & Database Queries ---")
        defects_res = requests.get(f"{BASE_URL}/api/defects", headers=headers, timeout=5)
        assert defects_res.status_code == 200
        defects_page = defects_res.json()
        assert defects_page["total"] >= 1
        print(f"  [PASS] Persisted defects count: {defects_page['total']}")

        # 6. Verify Dashboard Telemetry & Stats (/api/dashboard/stats)
        print("\n--- Testing Dashboard Analytics Aggregation ---")
        stats_res = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers, timeout=5)
        assert stats_res.status_code == 200
        stats = stats_res.json()
        print(f"  [PASS] Dashboard Stats: {stats}")

        print("\n=======================================================")
        print(" [ALL E2E INTEGRATION CHECKS PASSED SUCCESSFULLY 100%] ")
        print("=======================================================")

    finally:
        print("\n[E2E] Shutting down test server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_fp.close()
        print("[E2E] Server stopped cleanly.")

if __name__ == "__main__":
    run_e2e_verification()
