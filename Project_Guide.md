# 🛣️ RoadPulse AI — Project Guide

This guide explains the **RoadPulse AI** project in simple English, covering the **Why, What, How, Where, and When**.

---

## 1. WHY was this project built? (The Purpose)
Roads are the arteries of a nation. When roads develop potholes and distress, two major problems occur:
1.  **Public Safety Hazards**: Road damage causes vehicular accidents, injuries, and fatalities.
2.  **Compounding Maintenance Costs**: Unattended small cracks deteriorate rapidly into deep sub-base failures during monsoon cycles, costing 5x to 10x more to rehabilitate later.

**The Traditional Problem**: Municipalities depend on manual, ad-hoc road surveys. Human visual inspection is slow, subjective, hazardous, and covers less than 5% of the road network annually.  
**The Solution**: RoadPulse AI transforms ordinary dashcams and smartphones into autonomous, high-precision pavement inspection systems that detect defects, calculate calibrated 3D surface areas, and generate immediate CPWD/MoRTH repair budgets.

---

## 2. WHAT is it? (The Product)
RoadPulse AI is an **Autonomous Road Health Assessment & Pavement Repair Budgeting Platform**. 
- **Web Dashboard**: An executive and operational web platform featuring interactive GIS mapping, budget forecasting, and work-order dispatch.
- **Mobile Application**: A Flutter client for field engineers and citizens providing offline video capture, GPS track telemetry, and real-time defect reporting.
- **AI Vision Engine**: A YOLOv8 instance segmentation model that detects road distress at 30+ FPS and extracts polygon contour vertices.
- **Civil Engineering Calculator**: A geometry and Schedule of Rates (SOR) engine that calculates metric surface areas and itemized repair bills using IRC:82-2015 and CPWD standards.

### Key Capabilities:
- **Comprehensive 14-Class Taxonomy**: The data schema and CPWD rate book define 14 pavement distress categories (Potholes, Rutting, Alligator Cracking, Subsidence, Fretting, Bleeding, etc.).
- **Truth in AI (Ground-Truth Resolution)**: In strict accordance with engineering integrity, the vision model is trained and independently evaluated exclusively on verified annotated classes (**Class 0: Pothole** and **Class 13: Traffic_Sign**), achieving **0.672 mAP@50** and **0% cross-split data leakage** with zero data synthesis or metric fabrication.
- **Real-World Surface Area Calculation**: Applies camera perspective ray-casting and Green's Theorem (shoelace integration) to project pixel masks into metric dimensions ($m^2$).
- **5-Factor Rate Identity**: Accounts for base patching, traffic volume, terrain, urgency, and regional cost indices.
- **PCI Grading**: Automatically scores roads into Good, Fair, Poor, or Failed pavement condition indices (ASTM D6433).

---

## 3. HOW does it work? (The Architecture)

| Component | Technical Name | Role & Responsibility |
| :--- | :--- | :--- |
| **The Eyes** | YOLOv8s-seg Vision Model | Detects potholes and road assets in dashcam frames with instance contour masks. |
| **The Brain** | Geometry & Severity Engine | Projects 2D pixels to metric ground-plane coordinates and classifies severity per IRC:82. |
| **The Heart** | FastAPI REST Backend | Validates schemas, enforces RBAC, issues JWTs, and handles work-order lifecycle. |
| **The Ledger** | SQLite / PostgreSQL ORM | Persists defects, road networks, GPS coordinates, repair logs, and audit trails. |
| **The Face** | Web Dashboard (HTML5/JS) | Renders dark-themed GIS maps, defect image comparisons, and budget charts. |
| **The Hand** | Flutter Mobile Client | Records surveys with GPS sensor fusion and synchronizes offline field data. |

### The Workflow:
1. **Input**: A field surveyor mounts a smartphone or dashcam and drives along a road corridor.
2. **Detection**: YOLOv8 segments defects in real time at the native video frame rate.
3. **Metric Projection**: The geometry calibrator uses camera mount height and tilt angle to compute the metric area of each defect.
4. **Budgeting**: The SOR engine applies regional CPWD rates to determine the exact repair cost.
5. **Dispatch**: The administrator assigns the work order to a municipal field worker via the dashboard.

---

## 4. Quick Evaluation & Demo Guide

### Demo Credentials:
Baseline accounts are pre-seeded in the database:

| Role | Username | Password | Permitted Actions |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `AdminPass123!` or `admin123` | Full governance, user creation, work assignment, analytics |
| **Field Worker** | `worker` / `worker1` | `WorkerPass123!` or `worker123` | Task execution, repair status updates, image proofs |
| **Citizen User** | `user1` | `UserPass123!` or `user123` | Defect reporting, status tracking, public dashboard view |

### Quick Start Commands:
```powershell
# 1. Start FastAPI Backend Server
py main.py

# 2. Run Backend Pytest Suite (57/57 tests passing)
py -m pytest backend/app/tests -v

# 3. Run Mobile Widget Tests
cd mobile && flutter test test/widget_test.dart
```

---

## 5. WHERE is it used? (Use Cases)
- **Municipal Corporations (Smart Cities)**: Automate annual road audits and prioritize repair tenders objectively.
- **Highway Authorities (NHAI / MoRTH)**: Continuous monitoring of national corridors and tollway maintenance SLA verification.
- **Public Works Contractors**: Verify repair quality with tamper-proof "before" and "after" photographic records.
- **Insurance & Fleet Logistics**: Identify high-risk corridors to optimize delivery routes and reduce vehicle suspension wear.

---

## 6. WHEN does it deliver value?
- **Pre-Monsoon Audits**: Detect and seal hairline cracks before water penetration causes structural pavement collapse.
- **Post-Repair Quality Assurance**: Inspect newly patched surfaces to confirm contractor compliance with road smoothness standards.
- **Continuous Daily Patrol**: Fleet vehicles (buses, sanitation trucks) passively map road conditions every day without hiring specialized survey crews.

---

## 🏗️ Technical Stack Summary
- **Backend**: FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, Pytest (57 tests).
- **Computer Vision**: Ultralytics YOLOv8s-seg, PyTorch 2.x, OpenCV.
- **Mobile**: Flutter 3.x, Dart, Provider, SQLite / sqflite, Geolocator.
- **Frontend**: Vanilla JavaScript (ES6+), Leaflet.js, Chart.js, Lucide Icons.
- **DevOps**: Docker Multi-Stage Build, Docker Compose, GitHub Actions CI/CD.
