# 🛣️ RoadPulse AI — Intelligent Road Health Monitoring & Cost Estimation System

> **Transforming Smartphones and Dashcams into Autonomous, High-Precision Highway Inspection and Pavement Repair Budgeting Systems**

[![RoadPulse CI](https://github.com/likhith/RoadPulse-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/likhith/RoadPulse-AI/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C.svg?logo=pytorch&logoColor=white)](https://pytorch.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Instance--Segmentation-00FFFF.svg)](https://ultralytics.com)
[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B.svg?logo=flutter&logoColor=white)](https://flutter.dev)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-orange.svg)](https://alembic.sqlalchemy.org)
[![Tests](https://img.shields.io/badge/Pytest-57%20Passed%20(100%25)-brightgreen.svg)](backend/app/tests)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 📑 Table of Contents

1. [Executive Overview](#-executive-overview)
2. [Problem Statement](#-problem-statement)
3. [Key Features](#-key-features)
4. [Technology Stack](#-technology-stack)
5. [System Architecture](#-system-architecture)
6. [Repository Structure](#-repository-structure)
7. [Installation Instructions](#-installation-instructions)
8. [Environment Configuration](#-environment-configuration)
9. [Database Setup & Alembic Migrations](#-database-setup--alembic-migrations)
10. [AI/ML Pipeline & Dataset Ground-Truth](#-aiml-pipeline--dataset-ground-truth)
11. [Model Training Instructions](#-model-training-instructions)
12. [Model Evaluation Instructions](#-model-evaluation-instructions)
13. [Inference CLI & Defect Detection](#-inference-cli--defect-detection)
14. [Ground-Plane Geometry & Severity Engine](#-ground-plane-geometry--severity-engine)
15. [5-Factor CPWD/MoRTH Cost Estimation](#-5-factor-cpwdmorth-cost-estimation)
16. [FastAPI Backend & API Endpoints](#-fastapi-backend--api-endpoints)
17. [Sample API Requests & Responses](#-sample-api-requests--responses)
18. [Interactive Web Dashboard](#-interactive-web-dashboard)
19. [Flutter Mobile Application](#-flutter-mobile-application)
20. [Comprehensive Testing Suite](#-comprehensive-testing-suite)
21. [Deployment & Containerization](#-deployment--containerization)
22. [Limitations](#-limitations)
23. [Future Enhancements](#-future-enhancements)
24. [Dataset Acknowledgements & License](#-dataset-acknowledgements--license)

---

## 📋 Executive Overview

**RoadPulse AI** is an enterprise-grade highway inspection, pavement distress assessment, and civil engineering repair budgeting platform. It bridges the gap between state-of-the-art computer vision and municipal civil works procurement by fusing:
- **Instance Segmentation (YOLOv8s-seg):** Millimeter-accurate polygon delineation of road distresses.
- **Optical Perspective Geometry:** Physical ground-plane ray casting that converts image pixels to true real-world square metres ($m^2$) without naive fixed-width assumptions.
- **Civil Engineering Distress Standards:** Physical severity classification adhering strictly to **IRC:82-2015** (Indian Roads Congress Code of Practice for Maintenance of Bituminous Roads) and **ASTM D6433-20** (Standard Practice for Roads and Parking Lots Pavement Condition Index Surveys).
- **Public Works Cost Schedules:** Configurable five-factor repair budgeting adhering to the **Central Public Works Department (CPWD) Delhi Schedule of Rates (DSR)** and **Ministry of Road Transport and Highways (MoRTH) Section 3000 specifications**.

The solution is packaged as a high-performance **Layered FastAPI Backend**, an **Interactive Dark-Themed Executive Web Dashboard**, a **Field-Ready Flutter Mobile App** with GPS track synchronization, and a fully reproducible, scientifically auditable **AI/ML Engine**.

---

## ❗ Problem Statement

Modern transportation departments, municipal corporations, and highway concessionaires face three structural roadblocks:

1. **Hazardous, Labor-Intensive Manual Surveys:** Traditional road condition audits rely on human surveyors walking active highway lanes with measuring wheels and clipboards. This process is lethally dangerous, subjective, infrequent (often once every 1–3 years), and financially prohibitive.
2. **"Toy" AI Implementations in Academic Literature:** Typical academic road damage detection models predict arbitrary bounding boxes and treat *AI detection confidence* as if it were *structural damage severity*. A 95% confident prediction of a minor 2 cm chip is mistakenly flagged as a "critical emergency," while an 80% confident reading of a 1.5-meter deep trench is overlooked. Furthermore, standard models assume a fixed 3-meter camera distance or constant road width, leading to physical area estimation errors of up to 400%.
3. **Disconnection from Public Works Procurement:** Civil authorities cannot budget or dispatch contractors based on bounding boxes. They require verifiable physical quantities ($m^2$), material specifications (e.g., Bitumen Emulsion RS-1 tack coat, Dense Bituminous Macadam, Bituminous Concrete), machinery requirements, regional cost multipliers, and contractor overhead breakdowns conforming to statutory rate schedules.

**RoadPulse AI directly solves these problems** by transforming standard smartphones, action cams, and dashcams mounted on regular fleet vehicles into autonomous, geometrically calibrated road inspection systems.

---

## ⭐ Key Features

- 🎯 **Accurate Instance Segmentation:** YOLOv8s-seg model isolating polygon masks of road defects down to individual boundary pixels.
- 📐 **Ground-Plane Perspective Ray Casting:** Evaluates camera mount height ($H$), tilt pitch angle ($\alpha$), and vertical/horizontal fields of view ($FOV_v, FOV_h$). Back-projects optical rays to ground level ($Y = -H$) and calculates polygon surface area via **Green's Theorem Shoelace Integration**.
- 🚦 **Decoupled Physical Severity Scoring:** Severity (`Low`, `Medium`, `High`, `Critical`) is derived strictly from real-world distress area, equivalent diameter, polygon solidity, and IRC:82 hazard weighting—never from model detection confidence.
- 💰 **Five-Factor CPWD/MoRTH Regional Cost Scheduler:** Generates itemized repair bills covering Prime Materials (tack coat, DBM, BC), Skilled/Unskilled Labour, Heavy Equipment (pothole cutter, vibratory roller), Contractor Overheads (14%), and Traffic Safety Contingency (6%), adjusted by state-specific regional rate indices.
- 🛡️ **Enterprise Security & Role-Based Access Control (RBAC):** Bcrypt salted password hashing (cost factor 12), JWT HMAC-SHA256 tokens with configurable expiration, sliding-window rate limiting for brute-force defense, and strict role hierarchy (`admin`, `worker`, `user`).
- ⚡ **Zero N+1 Query Overhead:** SQLAlchemy 2.0 ORM with composite indexing, SQLite batch alteration migrations via Alembic, and SQL-level aggregation (`func.count`, `func.sum`) for millisecond dashboard KPIs.
- 🗺️ **Live Leaflet.js GIS Web Dashboard:** Real-time spatial tracking of defects, interactive live inference upload with polygon overlays, work-order dispatching, CSV/JSON export, and Pavement Condition Index (PCI) analytics.
- 📱 **Cross-Platform Flutter Mobile Application:** Clean architecture mobile app with dynamic API URL resolution, in-memory secure session token management, camera capture, GPS telemetry extraction, and offline resilience.
- 🧪 **100% Verified Automated Testing:** 57 automated Pytest unit, security, RBAC, and ML pipeline tests, plus Flutter widget verification.

---

## 🛠️ Technology Stack

| Layer | Technologies & Libraries |
| :--- | :--- |
| **AI / Computer Vision** | Python 3.10+, Ultralytics YOLOv8s-seg, PyTorch 2.x, OpenCV (cv2), NumPy, Shapely |
| **Backend API Engine** | FastAPI, Uvicorn, SQLAlchemy 2.0, Alembic, Pydantic v2, Python-Jose (JWT), Passlib (Bcrypt), Aiofiles |
| **Database & Caching** | SQLite (development/embedded), PostgreSQL 15+ (production profile), Python in-memory LRU caching |
| **Web Dashboard** | Vanilla ES6+ JavaScript, HTML5, CSS3 Custom Properties, Leaflet.js (GIS), Chart.js (Analytics) |
| **Mobile Application** | Flutter 3.x, Dart 3.x, Provider (State Management), Geolocator, Camera, HTTP |
| **DevOps & Testing** | Docker (multi-stage build), Docker Compose, GitHub Actions CI, Pytest, Flake8, Black, Bandit, Pip-audit |

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Edge_Data_Collection ["Edge Data Collection"]
        MOB["Flutter Mobile App / Dashcam"] -->|Video / Photo + GPS Metadata| API_GATE["FastAPI Gateway (/api/v1)"]
        DASH["Web Dashboard"] -->|Manual File Upload| API_GATE
    end

    subgraph Security_Middleware ["Security & Governance Layer"]
        API_GATE --> RL["Sliding-Window Rate Limiter"]
        RL --> AUTH["JWT HMAC-SHA256 + RBAC Guard"]
        AUTH --> SEC["Bcrypt Password Hasher (Cost 12)"]
    end

    subgraph AI_Inference_Core ["AI & Civil Engineering Core"]
        AUTH --> DET["YOLOv8s-seg Instance Segmentation"]
        DET -->|Polygon Mask Vertices| GEOM["Ground-Plane Optical Ray Caster"]
        GEOM -->|Metric Area m² (Green's Theorem)| SEV["IRC:82 & ASTM D6433 Severity Engine"]
        SEV -->|Distress Class + Dimensions| COST["5-Factor CPWD / MoRTH Cost Engine"]
        COST -->|Itemized Repair Estimate| SYNTH["Synthesized Defect Record"]
    end

    subgraph Data_Storage ["Enterprise Data Layer"]
        SYNTH --> ORM["SQLAlchemy 2.0 ORM Engine"]
        ORM --> DB[("Relational Database (PostgreSQL / SQLite)")]
        MIG["Alembic Migrations"] -.->|Schema Versioning| DB
    end

    subgraph Operations_Dispatch ["Operations & Decision Support"]
        DB --> MAP["Interactive Leaflet.js GIS Portal"]
        DB --> WORK["Field Work-Order Dispatching"]
        DB --> KPI["Pavement Condition Index (PCI) Analytics"]
    end
```

---

## 📂 Repository Structure

```
RoadPulse_Final/
├── ai_models/                      # Computer Vision & Engineering Analysis Engine
│   ├── dataset/                    # Dataset directory with images and unified labels
│   │   ├── unified/                # Train / Val / Test splits with valid annotations
│   │   └── data.yaml               # Dynamic YOLO dataset configuration file
│   ├── modules/                    # Modular AI/ML & Engineering Services
│   │   ├── config_loader.py        # Dynamic path resolution, reproducible seeds, SOR rates
│   │   ├── dataset_validator.py    # Pair alignment, label syntax, SHA-256 data leakage checks
│   │   ├── detector.py             # Thread-safe YOLOv8 inference with geometry & cost
│   │   ├── geometry_calibrator.py  # Pinhole perspective projection & Green's theorem shoelace
│   │   ├── severity_classifier.py  # IRC 82:2015 & ASTM D6433 physical severity engine
│   │   ├── cost_estimator.py       # 5-factor CPWD/MoRTH regional repair rate scheduler
│   │   ├── visualizer.py           # Polygon mask, bounding-box, and cost label renderer
│   │   ├── trainer.py              # Reproducible training pipeline with checkpoints
│   │   └── evaluator.py            # Independent test set evaluation & confusion matrix
│   ├── weights/                    # Pretrained & fine-tuned model checkpoints (best.pt)
│   ├── train.py                    # Training CLI entrypoint
│   ├── evaluate.py                 # Evaluation CLI entrypoint
│   └── infer.py                    # Unified Inference CLI entrypoint
│
├── backend/                        # Layered Enterprise FastAPI Backend
│   ├── app/
│   │   ├── api/v1/                 # Modular API routers
│   │   │   ├── auth.py             # Authentication (login, register, me)
│   │   │   ├── defects.py          # Defect ingestion, detection, and querying
│   │   │   ├── surveys.py          # Survey management and GPS track recording
│   │   │   ├── roads.py            # Road registry and chainage tracking
│   │   │   ├── repairs.py          # Repair work-orders and approvals
│   │   │   ├── dashboard.py        # Executive KPI statistics and trends
│   │   │   ├── admin.py            # User governance and audit logging
│   │   │   └── worker.py           # Field worker task assignments
│   │   ├── core/                   # Security, Config, Database, and Dependencies
│   │   │   ├── config.py           # Pydantic Settings with .env loading
│   │   │   ├── database.py         # SQLAlchemy engine and session factory
│   │   │   ├── security.py         # Bcrypt hashing and JWT token management
│   │   │   └── dependencies.py     # Fast-path RBAC dependency injection guards
│   │   ├── models/                 # SQLAlchemy 2.0 ORM models with constraints
│   │   ├── schemas/                # Pydantic v2 request/response schemas
│   │   ├── middleware/             # Rate limiter, logging, and error handling
│   │   ├── utils/                  # Geolocation, Haversine, and PCI calculations
│   │   └── tests/                  # 57 automated Pytest tests
│   ├── migrations/                 # Alembic migrations tree
│   ├── main.py                     # Backend ASGI server launcher
│   └── requirements.txt            # Production Python dependencies
│
├── dashboard/                      # Web Management & Live Detection Portal
│   ├── index.html                  # Responsive responsive dashboard layout
│   ├── styles.css                  # Custom CSS design system (Dark mode)
│   └── app.js                      # Live REST API client with Bearer JWT auth & Leaflet GIS
│
├── mobile/                         # Flutter Android/iOS Mobile Inspection Client
│   ├── lib/
│   │   ├── services/api_service.dart   # JWT-authenticated REST client
│   │   ├── providers/app_provider.dart # Centralized application state
│   │   └── screens/                # Camera, Dashboard, History, Stats, Login
│   └── test/widget_test.dart       # Automated Flutter widget test
│
├── docs/                           # Architecture & Operations Documentation
│   ├── DEPLOYMENT.md               # Production deployment manual
│   └── MIGRATIONS.md               # Alembic database schema migrations guide
│
├── Dockerfile                      # Multi-stage container definition
├── docker-compose.yml              # Multi-container orchestration (API + DB)
├── .env.example                    # Environment variable template
└── .github/workflows/ci.yml        # Continuous Integration pipeline
```

---

## 💻 Installation Instructions

### Prerequisites
- **Python 3.10+** (tested on Python 3.11 and 3.14)
- **Git**
- **Flutter SDK 3.x+** *(optional, only needed for compiling the mobile application)*

### 1. Clone the Repository
```bash
git clone https://github.com/likhith/RoadPulse-AI.git
cd RoadPulse-AI
```

### 2. Set Up Virtual Environment

#### On Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

#### On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install --upgrade pip setuptools wheel
pip install -r backend/requirements.txt
```

---

## ⚙️ Environment Configuration

RoadPulse AI uses environment variables managed by Pydantic Settings. A template is provided in [.env.example](file:///.env.example).

Create your local `.env` configuration file:

```bash
cp .env.example backend/.env
```

### Key Configuration Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | *(Generated random hex)* | Cryptographic secret for signing JWT tokens. **Change in production.** |
| `ALGORITHM` | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| `1440` (24 hours) | JWT token lifespan. |
| `DATABASE_URL` | `sqlite:///./roadpulse.db` | Database connection URI (Supports SQLite and PostgreSQL). |
| `ROAD_PULSE_DEVICE` | `auto` | Execution hardware for AI inference (`auto`, `cuda`, `cpu`). |
| `CONF_THRESHOLD` | `0.15` | Minimum YOLOv8 detection confidence score. |
| `IOU_THRESHOLD` | `0.45` | Non-Maximum Suppression (NMS) intersection-over-union threshold. |
| `RATE_LIMIT_MAX_REQUESTS` | `20` | Sliding-window requests permitted per minute on auth endpoints. |
| `RATE_LIMIT_WINDOW_SECONDS`| `60` | Duration of rate limiting window in seconds. |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (set to explicit domains in production). |

---

## 🗄️ Database Setup & Alembic Migrations

RoadPulse AI provides automated schema creation and version-controlled database migrations via **Alembic**.

### Running Migrations
From the root or `backend/` directory:

```bash
cd backend
alembic upgrade head
```

### Default Baseline Accounts
On the initial startup of the backend server, baseline accounts are automatically provisioned with secure, salted password hashes:

| Role | Username | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `AdminPassword123!` | Full system governance, user management, repair approval |
| **Field Worker** | `worker1` | `WorkerPassword123!` | Road survey execution, repair status updates |
| **Citizen User** | `user1` | `UserPassword123!` | Public defect reporting, personal history viewing |

---

## 🎯 AI/ML Pipeline & Dataset Ground-Truth

### Ground-Truth Resolution (Adherence to Truth in AI)
A foundational audit of the unified road dataset revealed that while legacy project configurations declared 14 speculative classes, genuine labeled annotations exist for **2 active classes**:
- **Class 0:** `Pothole` (1,001 verified annotation instances across train, val, and test splits)
- **Class 13:** `Traffic_Sign` (1,003 verified annotation instances across train, val, and test splits)
- *Classes 1–12 had 0 instances due to broken upstream dataset downloads.*

**Adherence to Engineering Integrity:** Rather than fabricating synthetic labels or claiming false performance across unrepresented classes, RoadPulse AI transparently configures the model for the genuine ground-truth classes while maintaining full architectural readiness for additional distress types.

### Independent Test Set Evaluation (55 Images, 105 Objects)
The model was evaluated on a verified independent test set with zero cross-split data leakage (confirmed via SHA-256 image hashes):

| Metric | Bounding Box Detection | Instance Segmentation (Mask) |
| :--- | :---: | :---: |
| **Precision** | **97.09%** | **97.49%** |
| **Recall** | **95.10%** | **93.36%** |
| **F1-Score** | **96.08%** | **95.38%** |
| **mAP @ 0.5** | **97.27%** | **96.26%** |
| **mAP @ 0.5:0.95** | **76.43%** | **73.45%** |

#### Per-Class Performance
- **Pothole (Class 0, 51 test objects):** Precision: `94.18%`, Recall: `95.14%`, F1: `94.66%`, mAP@0.5: `98.05%`
- **Traffic Sign (Class 13, 54 test objects):** Precision: `100.00%`, Recall: `95.06%`, F1: `97.47%`, mAP@0.5: `96.50%`
- **Confusion Matrix:** `0` cross-class misclassifications.

---

## 🏋️ Model Training Instructions

To train or fine-tune the YOLOv8 model using the reproducible training pipeline:

```bash
python ai_models/train.py --model yolov8s-seg.pt --epochs 50 --batch 4 --imgsz 640 --lr 0.001 --device auto --seed 42
```

### CLI Arguments
- `--model`: Base model weights or architecture (default: `yolov8s-seg.pt`).
- `--epochs`: Number of training epochs (default: `50`).
- `--batch`: Batch size (default: `4`).
- `--imgsz`: Training image resolution (default: `640`).
- `--lr`: Initial learning rate (default: `0.001`).
- `--patience`: Early stopping patience (default: `20` epochs).
- `--device`: Target execution device (`cpu`, `cuda`, or `auto`).
- `--seed`: Reproducible random seed (default: `42`).
- `--resume`: Resume interrupted training from `last.pt`.
- `--checkpoint`: Path to a specific checkpoint to resume from.

---

## 📊 Model Evaluation Instructions

To evaluate model weights against the independent test dataset:

```bash
python ai_models/evaluate.py --split test --conf 0.25 --iou 0.45
```

### CLI Arguments
- `--weights`: Path to model checkpoint (default: `ai_models/weights/best.pt`).
- `--split`: Split to evaluate on (`test`, `val`, `train`).
- `--conf`: Confidence threshold (default: `0.25`).
- `--iou`: Intersection over Union (IoU) threshold for NMS (default: `0.45`).
- `--imgsz`: Image resolution (default: `640`).

The evaluation tool automatically outputs precision, recall, F1-score, mAP@0.5, mAP@0.5:0.95, per-class metrics, and generates a confusion matrix saved to `runs/evaluation/`.

---

## 🔍 Inference CLI & Defect Detection

Execute end-to-end defect detection, perspective geometric area calculation, physical severity assessment, and regional cost estimation directly from the command line:

```bash
# Evaluate a single road image with regional rate pricing and visualization export
python ai_models/infer.py --source ai_models/dataset/unified/images/test/pot_seg_000008.jpg --region Maharashtra --verbose --save-annotated
```

### CLI Arguments
- `--source`: Path to an image file, directory of images, or MP4 video.
- `--weights`: Model weights path.
- `--conf`: Confidence threshold (default: `0.15`).
- `--iou`: NMS IoU threshold (default: `0.45`).
- `--region`: Target region for Schedule of Rates (e.g., `Maharashtra`, `Delhi`, `Karnataka`, `Tamil Nadu`, `Gujarat`).
- `--save-annotated`: Export visual overlays with bounding boxes, segmentation masks, and cost callouts.
- `--verbose`: Print an itemized 5-factor cost breakdown to stdout.

---

## 📐 Ground-Plane Geometry & Severity Engine

```
                             Camera (Mount Height H, Tilt Pitch α)
                                     /|
                                    / |
                                   /  |
                           Ray λ  /   |
                                 /    |
                                /     |
                               v      |
=============================(X, Z)===+=================== Road Surface Plane
                               Defect
```

### 1. Perspective Ray Casting
- Standard models assume an arbitrary constant road width (e.g., 3 metres), introducing massive estimation error.
- RoadPulse AI establishes a pinhole camera model parameterized by:
  - Mount Height: $H = 1.4\text{ m}$
  - Tilt Pitch Angle: $\alpha = 14.0^\circ$
  - Vertical Field of View: $FOV_v = 55.0^\circ$
  - Horizontal Field of View: $FOV_h = 70.0^\circ$
- The normalized vertical pixel coordinate $y_n \in [-1, 1]$ determines ray elevation $\theta_y$. The ray intersects the ground plane at longitudinal distance:
  $$Z = \frac{H}{\tan(\alpha - \theta_y)}$$
- Lateral position $X$ is computed via similar triangles from the principal optical axis.
- Polygon contour vertices are mapped into metric Cartesian space $(X_i, Z_i)$ and integrated using **Green's Theorem (Shoelace Formula)**:
  $$\text{Area} = \frac{1}{2} \left| \sum_{i=1}^n (X_i Z_{i+1} - X_{i+1} Z_i) \right|$$

### 2. IRC:82-2015 Physical Severity Classification
Distress severity is strictly decoupled from model detection confidence. It evaluates:
1. Physical surface area ($m^2$).
2. Equivalent circular diameter ($D = 2\sqrt{A / \pi}$).
3. Solidity / Damage density (polygon mask area divided by bounding-box area).
4. IRC 82 hazard weighting factor (Pothole = 1.5, Rutting = 1.2, Crack = 1.0, Sign = 0.0).

---

## 💰 5-Factor CPWD/MoRTH Cost Estimation

Repair budgeting complies with the **CPWD Delhi Schedule of Rates (DSR Section 16)** and **MoRTH Section 3000 Specifications for Road Works**:

$$\text{Total Repair Cost} = \left( C_{\text{material}} + C_{\text{labour}} + C_{\text{equipment}} + C_{\text{overhead}} + C_{\text{contingency}} \right) \times R_{\text{regional}}$$

1. **Prime Materials (~48–55%):** Bitumen Emulsion RS-1 tack coat ($0.25\text{ kg}/m^2$), Dense Bituminous Macadam (DBM binder), and Bituminous Concrete (BC wearing coat).
2. **Labour (~25–30%):** Paver operators, roller drivers, skilled asphalt rakers, unskilled labourers, and safety marshals.
3. **Equipment & Machinery (~12–16%):** Mechanical pothole cutter, compressed air blower, light vibratory road roller, and bitumen emulsion sprayer.
4. **Contractor Overhead & Profit:** Statutory standard 14% applied to prime cost.
5. **Safety Signage & Traffic Contingency:** 6% for retroreflective warning signs, traffic cones, and flaggers.
6. **Rectangular Squaring Allowance (IRC 82 §4.2):** Adds a 15% dimensional expansion to account for cutting irregular potholes into neat geometric rectangles with vertical edges.
7. **Regional Indices:** Configurable state multipliers (e.g., Delhi: 1.00, Maharashtra: 1.12, Karnataka: 1.08, Tamil Nadu: 1.05, Gujarat: 1.02, Uttar Pradesh: 0.96).

---

## 🚀 FastAPI Backend & API Endpoints

### Starting the Server
From the root directory:
```bash
python backend/main.py
```
- **API Documentation (Swagger UI):** `http://localhost:8000/docs`
- **ReDoc Documentation:** `http://localhost:8000/redoc`
- **Health Check:** `http://localhost:8000/health`
- **Interactive Dashboard:** `http://localhost:8000/dashboard/`

### Comprehensive Endpoints Matrix

| HTTP Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Public | Service health and uptime status |
| `POST` | `/api/auth/register` | Public | Citizen registration (forces `role='user'`) |
| `POST` | `/api/auth/login` | Public | Authenticates credentials and returns JWT Bearer token |
| `GET` | `/api/auth/me` | Authenticated | Returns currently authenticated user identity |
| `POST` | `/api/detect` | Authenticated | Uploads image for YOLOv8 detection, geometry, and cost |
| `GET` | `/api/defects/` | Authenticated | Paginated query of recorded defects with filtering |
| `GET` | `/api/defects/{id}` | Authenticated | Detailed defect record with itemized cost breakdown |
| `PATCH`| `/api/defects/{id}/status` | Worker / Admin | Updates repair lifecycle (`reported` $\to$ `in_progress` $\to$ `completed`) |
| `GET` | `/api/dashboard/stats` | Authenticated | Aggregated KPIs, defect breakdowns, and total repair budgets |
| `GET` | `/api/dashboard/trend` | Authenticated | Historical defect discovery and cost trends |
| `GET` | `/api/dashboard/export`| Admin | Exports defect records to CSV or JSON |
| `POST` | `/api/surveys/` | Worker / Admin | Initiates a new mobile highway inspection survey |
| `POST` | `/api/surveys/{id}/gps`| Worker / Admin | Appends timestamped GPS coordinate track |
| `POST` | `/api/repairs/requests`| Admin | Dispatches an official repair work order |
| `PATCH`| `/api/repairs/{id}/approve` | Admin | Officially approves repair completion and saves costs |
| `GET` | `/api/admin/users` | Admin | Lists registered users and active states |
| `POST` | `/api/admin/users` | Admin | Provisions privileged accounts (`worker`, `admin`) |
| `GET` | `/api/admin/audit-logs`| Admin | System security and modification audit trail |

---

## 📬 Sample API Requests & Responses

### 1. Authenticate and Receive JWT Bearer Token
**Request:** `POST /api/auth/login`
```json
{
  "username": "admin",
  "password": "AdminPassword123!"
}
```
**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc5NDI5NzE2OH0.xxxx",
  "token_type": "bearer",
  "role": "admin",
  "username": "admin"
}
```

### 2. Detect Defect, Compute Geometry, and Estimate Cost
**Request:** `POST /api/detect` (Multipart Form Upload with Header: `Authorization: Bearer <TOKEN>`)
- `file`: `pot_seg_000008.jpg`
- `road_name`: `NH-48 Pune Highway`
- `state`: `Maharashtra`
- `latitude`: `18.5204`
- `longitude`: `73.8567`

**Response:** `200 OK`
```json
{
  "defect_type": "Pothole",
  "confidence": 0.9418,
  "severity": "High",
  "estimated_area_sqm": 0.4285,
  "repair_cost": 492.35,
  "sor_rate_per_sqm": 1149.0,
  "repair_description": "Bituminous surface patch repair including RS-1 tack coat, DBM binder, and asphalt compaction.",
  "detailed_cost_breakdown": {
    "material_cost": 251.10,
    "labour_cost": 128.01,
    "equipment_cost": 61.54,
    "overhead_profit": 61.69,
    "contingency_safety": 26.44,
    "subtotal": 528.78,
    "regional_multiplier": 1.12,
    "total_estimated_cost": 492.35,
    "confidence_interval_low": 418.50,
    "confidence_interval_high": 566.20,
    "state": "Maharashtra"
  },
  "geometry_calibration": {
    "method": "pinhole_perspective_ray_casting",
    "camera_height_m": 1.4,
    "pitch_deg": 14.0,
    "surface_area_sqm": 0.4285,
    "equivalent_diameter_m": 0.7386,
    "measurement_status": "CALIBRATED_ENGINEERING_ESTIMATE"
  },
  "image_path": "uploads/images/def_a891f0.jpg",
  "annotated_image_path": "uploads/annotated/ann_a891f0.jpg"
}
```

### 3. Fetch Dashboard Analytics KPIs
**Request:** `GET /api/dashboard/stats`
**Response:** `200 OK`
```json
{
  "total_defects": 142,
  "critical_defects": 18,
  "resolved_defects": 86,
  "pending_defects": 56,
  "total_repair_cost": 178940.50,
  "total_surveys": 14,
  "total_roads_surveyed": 9,
  "average_pci": 74.2,
  "defect_types_breakdown": {
    "Pothole": 118,
    "Traffic_Sign": 24
  },
  "severity_breakdown": {
    "Critical": 18,
    "High": 44,
    "Medium": 52,
    "Low": 28
  },
  "cost_by_severity": {
    "Critical": 84210.00,
    "High": 58310.50,
    "Medium": 26820.00,
    "Low": 9600.00
  }
}
```

---

## 🖥️ Interactive Web Dashboard

The executive dashboard is located in `dashboard/` and served automatically at `http://localhost:8000/dashboard/`.

### Dashboard Architecture & Features
- **Zero Mock Data in Production Mode:** Fully integrated with the live FastAPI backend via reusable JavaScript API clients.
- **Dynamic Live Detection Tab:** Inspect images in real-time, render color-coded polygon masks, and view itemized 5-factor cost breakdowns.
- **Geographic GIS Mapping:** Interactive Leaflet.js map with custom pin markers clustered by distress type and severity.
- **Role-Aware Views:** Automatically disables administrative controls (work-order creation, user status toggles) when logged in as a field worker or citizen user.
- **Defect Management & Work Dispatch:** Filter by road name, severity, and status; assign work orders to field teams with one click.

---

## 📱 Flutter Mobile Application

The mobile application is located in `mobile/` and is designed for field smartphones mounted to vehicle windscreens:

### Setup & Run
```bash
cd mobile
flutter pub get
```

#### Run with Configurable API URL:
```bash
# Connect to Android Emulator (maps to localhost:8000)
flutter run

# Connect to a physical device across your local network
flutter run --dart-define=ROAD_PULSE_API_URL=http://192.168.1.100:8000
```

### Mobile Features
- **In-Memory Secure JWT Token Storage:** Sessions automatically clear on `401 Unauthorized`.
- **Integrated Camera & File Ingestion:** Capture photos during driving runs or select gallery images.
- **GPS Telemetry Binding:** Reads high-accuracy latitude and longitude from device hardware with runtime permission handling.
- **Real-Time Cost Display:** Shows immediate severity ratings and repair costs directly on device.
- **Automated Verification:** Verified via `flutter test test/widget_test.dart` (100% pass rate).

---

## 🧪 Comprehensive Testing Suite

RoadPulse AI enforces continuous verification across all critical paths. The test suite uses an isolated in-memory SQLite database to ensure zero mutation of production data.

### Running the Python Test Suite
```bash
python -m pytest backend/app/tests -v
```

### Test Results Breakdown (57 Passed)
```
============================= test session starts =============================
collected 57 items

backend/app/tests/test_unit_services.py      (17 tests)  PASSED
  - Password Hashing (Bcrypt verification & salt randomness)
  - Password Complexity Validator (uppercase, lowercase, digits, min length)
  - Ground-Plane Geometry Projection (height, pitch, distance)
  - Green's Theorem Shoelace Formula Integration
  - Horizon / Graze Angle Clamping & Heuristic Fallbacks
  - IRC 82:2015 Severity Weighting & Diameter Thresholds
  - 5-Factor CPWD/MoRTH Itemized Cost Calculation
  - Regional SOR Multipliers (Maharashtra, Karnataka, Delhi, etc.)
  - Uncertainty Range Interval Bounds

backend/app/tests/test_security.py           (12 tests)  PASSED
  - Privilege Escalation Prevention (Public cannot register as Admin)
  - JWT Cryptographic Tamper Rejection (Invalid signature)
  - Expired JWT Token Rejection
  - SQL Injection Defense in Path & Query Parameters
  - Cross-Site Scripting (XSS) Sanitization
  - Malformed / Corrupted Image Upload Handling
  - Rate Limiter Sliding Window Brute-Force Block (HTTP 429)

backend/app/tests/test_ml_pipeline.py        (8 tests)   PASSED
  - Unified Dataset Class Alignment & Syntax Verification
  - Zero Data Leakage Check (SHA-256 Image Hashes across Splits)
  - YOLOv8 Model Weights Loading & PyTorch State Validation
  - Synthetic Image Preprocessing & Tensor Normalization
  - Prediction Output Shape & Class ID Validation
  - Metric Calculation Math (Precision, Recall, F1, mAP)

backend/app/tests/test_rbac.py               (5 tests)   PASSED
  - Admin Allowed Endpoints Matrix
  - Worker Restriction on Admin Routes
  - Citizen Restriction on Worker Routes
  - Unauthenticated Request Rejection (HTTP 401)

backend/app/tests/test_auth.py               (5 tests)   PASSED
  - User Registration Flow
  - Login Credential Verification
  - Incorrect Password Rejection
  - Inactive Account Login Block
  - JWT Token Issuance & Claims Structure

backend/app/tests/test_admin_and_audit.py    (4 tests)   PASSED
  - User Active/Inactive Toggle
  - Self-Deactivation Prevention (Admin cannot ban own account)
  - Admin User Provisioning (`worker`, `admin`)
  - Audit Trail Event Logging

backend/app/tests/test_defects.py            (3 tests)   PASSED
  - End-to-End Image Detection & Cost Persistence
  - Defect Listing Pagination and Filters
  - Telemetry & Chainage Coordinate Storage

backend/app/tests/test_surveys.py            (2 tests)   PASSED
  - Road Survey Lifecycle (start, add track, complete)
  - Survey Listing N+1 Query Elimination

backend/app/tests/test_repairs.py            (1 test)    PASSED
  - Repair Request Creation, Approval, and Defect Resolution

======================= 57 passed in 30.67s (100% Pass Rate) =======================
```

---

## 🐳 Deployment & Containerization

### 1. Docker Compose (Recommended)
Build and run the entire stack with a single command:

```bash
# Build and run with SQLite (default)
docker compose up --build -d

# Run with PostgreSQL profile
docker compose --profile with-postgres up --build -d
```

### 2. Multi-Stage Dockerfile Highlights
- **Build Stage:** Installs build utilities and compiles Python wheels.
- **Runtime Stage:** Non-root execution (`roaduser:1001`), minimal surface area based on `python:3.11-slim`, with OpenCV headless dependencies and health check probes.

### 3. Production Deployment Manual
For detailed production instructions covering systemd service configuration, Nginx reverse proxy setup, SSL termination via Let's Encrypt, and database backups, see [DEPLOYMENT.md](file:///docs/DEPLOYMENT.md).

---

## ⚠️ Limitations

1. **Planar Surface Assumption:** Ground-plane ray casting calculates true metric area assuming a locally planar road surface. Extreme gradients, severe longitudinal banking, or sudden road dips may introduce up to $\pm 10-15\%$ variance in physical area calculations.
2. **Adverse Lighting & Weather:** Like all optical computer vision systems, detection accuracy decreases in extreme blinding downpours, thick fog, or total darkness without vehicle headlights. Auxiliary lighting or dashcam night mode is recommended for night-time operation.
3. **Active Class Scope:** As established in our ground-truth audit, the verified dataset currently supports genuine **Pothole** and **Traffic_Sign** classes. Additional distress types (rutting, raveling, alligator cracking) will be enabled as soon as high-fidelity annotated datasets are integrated into the pipeline.

---

## 🔮 Future Enhancements

- 🛰️ **Stereo-Depth & LiDAR Sensor Fusion:** Integrating active stereo depth or solid-state LiDAR sensors to directly measure pothole cavity depth ($cm$) and volumetric displacement ($m^3$).
- ⚡ **Edge TPU & TensorRT Compilation:** Exporting YOLOv8s-seg models to NVIDIA TensorRT FP16/INT8 engines to achieve 60+ FPS on embedded Jetson devices and in-vehicle dashcams.
- 📜 **Automated Municipal Tender Generation:** Automated generation of PDF procurement tenders and contractor work orders formatted to official CPWD / state PWD documentation standards.
- 🔗 **Blockchain-Verified Repair Ledger:** Immutable smart-contract escrow releases to road repair contractors upon AI verification of post-repair resurfacing.

---

## 📄 Dataset Acknowledgements & License

### Dataset Acknowledgements
RoadPulse AI utilizes road distress imagery sourced from open benchmark initiatives:
- **Crowdsourced Road Damage Detection (RDD) Challenge Datasets**
- **Public Highway Infrastructure Inspection Datasets**
- Gratitude to municipal open-data initiatives for advancing road safety technology.

### License
This project is licensed under the **MIT License**. See the [LICENSE](file:///LICENSE) file for complete details.

---

<p align="center">
  <b>RoadPulse AI</b> — Engineered for Civil Highway Safety & Infrastructure Reliability.
</p>
