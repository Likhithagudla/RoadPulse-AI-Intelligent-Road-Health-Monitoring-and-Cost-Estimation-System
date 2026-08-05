# 🛣️ RoadPulse AI — Intelligent Road Assessment System

> **Turning a Smartphone into an Automatic Road Inspector**

An AI-powered road defect detection and assessment system that uses computer vision (YOLOv8) to automatically identify road defects, estimate repair costs using SOR rates, and display everything on an interactive dark-themed dashboard.

---

## 📁 Project Structure

```
D:\Road_AI_Project\
├── ai_models\                    # AI/ML Components
│   ├── config.yaml               # YOLOv8 dataset configuration (14 classes)
│   ├── requirements.txt          # Python dependencies for AI
│   ├── dataset\                  # Downloaded datasets
│   │   ├── unified\              # Unified dataset (train/val/test splits)
│   │   ├── Mendeley_Rutting\     # Mendeley rutting data
│   │   ├── road-damage-detection\
│   │   └── potholes-cracks-and-openmanholes-road-hazards\
│   ├── scripts\
│   │   ├── prepare_dataset.py    # Dataset unification & format conversion
│   │   ├── train_model.py        # YOLOv8 training pipeline
│   │   ├── detection_service.py  # Inference service (used by FastAPI)
│   │   ├── master_download.py    # Dataset download script
│   │   └── setup_info.py         # Project setup checker
│   ├── weights\                  # Trained model weights (best.pt, last.pt)
│   ├── runs\                     # Training run logs & metrics
│   └── exported_models\          # ONNX exports for deployment
│
├── backend\                      # FastAPI Backend
│   ├── main.py                   # API endpoints (detect, surveys, reports, etc.)
│   ├── models.py                 # SQLAlchemy models (RoadDefect, Survey, Road, SOR)
│   ├── database.py               # PostgreSQL connection
│   ├── requirements.txt          # Backend dependencies
│   ├── .env                      # Database credentials
│   └── run_server.bat            # Start server script
│
├── dashboard\                    # RoadPulse AI Dashboard
│   ├── index.html                # Main dashboard page
│   ├── styles.css                # Premium dark theme CSS
│   └── app.js                    # Dashboard application logic
│
└── mobile\                       # Mobile App (Phase 4 - future)
```

---

## 🚀 Quick Start

### 1. Install AI Dependencies
```bash
cd D:\Road_AI_Project\ai_models
pip install -r requirements.txt
```

### 2. Prepare Dataset
```bash
cd D:\Road_AI_Project\ai_models\scripts

# Download datasets (requires Kaggle API key)
python master_download.py

# Unify all datasets into train/val/test splits
python prepare_dataset.py
```

### 3. Train the Model
```bash
python train_model.py --mode train
# Or full pipeline (train + validate + export + test):
python train_model.py --mode full
```

### 4. Install Backend Dependencies
```bash
cd D:\Road_AI_Project\backend
pip install -r requirements.txt
```

### 5. Start the API Server
```bash
cd D:\Road_AI_Project\backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Open the Dashboard
- Open `D:\Road_AI_Project\dashboard\index.html` in your browser
- Or visit `http://localhost:8000/dashboard/` when the API server is running

### 7. Seed Demo Data (Optional)
```bash
# POST to seed demo data into the database
curl -X POST http://localhost:8000/api/seed-demo-data
```

---

## 🎯 14 Detection Classes

| # | Defect Type | Category |
|---|---|---|
| 0 | Pothole | Road Defect |
| 1 | Edge Deterioration | Road Defect |
| 2 | Alligator Cracking | Road Defect |
| 3 | Rutting | Road Defect |
| 4 | Subsidence | Road Defect |
| 5 | Cracking | Road Defect |
| 6 | Bleeding | Road Defect |
| 7 | Fretting | Road Defect |
| 8 | Repaired Pothole | Road Defect |
| 9 | Line Marking | Infrastructure |
| 10 | Storm Drain | Infrastructure |
| 11 | Manhole | Infrastructure |
| 12 | Guard Rail | Infrastructure |
| 13 | Traffic Sign | Infrastructure |

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | System health check |
| POST | `/api/detect` | Upload image for AI detection |
| POST | `/api/detect/video` | Upload video for batch processing |
| GET | `/api/defects` | List all defects (filterable) |
| GET | `/api/defects/map` | GeoJSON data for map markers |
| POST | `/api/surveys` | Create new survey |
| GET | `/api/surveys` | List all surveys |
| POST | `/api/roads` | Add road to registry |
| GET | `/api/roads` | List all roads |
| GET | `/api/dashboard/stats` | Dashboard statistics |
| GET | `/api/dashboard/trends` | Detection trends over time |
| GET | `/api/reports/summary` | Generate summary report |
| POST | `/api/seed-demo-data` | Seed database with demo data |

---

## 💰 SOR Cost Estimation

The system uses **Schedule of Rates (SOR)** based on IRC/MORTH guidelines to estimate repair costs per defect:

| Defect | Low (₹/sqm) | Medium (₹/sqm) | High (₹/sqm) |
|--------|-------------|-----------------|---------------|
| Pothole | 350 | 550 | 850 |
| Alligator Cracking | 200 | 600 | 1,200 |
| Rutting | 300 | 700 | 1,500 |
| Subsidence | 400 | 900 | 2,000 |
| Cracking | 150 | 400 | 800 |

---

## 🗺️ Development Roadmap

- [x] **Phase 1**: FastAPI Backend + Database
- [x] **Phase 2**: AI Model Training Pipeline (YOLOv8)
- [x] **Phase 3**: RoadPulse AI Dashboard
- [ ] **Phase 4**: Flutter Mobile App (Driver's App)
- [ ] **Phase 5**: Deploy to Cloud (AWS/GCP)

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Model | YOLOv8 (Ultralytics) |
| Backend | FastAPI + SQLAlchemy |
| Database | PostgreSQL |
| Dashboard | HTML/CSS/JS + Leaflet + Chart.js |
| Maps | Leaflet + CARTO Dark Tiles |
| Icons | Lucide Icons |
| Mobile | Flutter (Phase 4) |
