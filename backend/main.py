"""
============================================================
Road AI Assessment API - Enhanced FastAPI Backend
============================================================
Endpoints:
  - /api/detect         : Upload image for defect detection
  - /api/detect/video   : Upload video for processing
  - /api/surveys        : CRUD for road surveys
  - /api/defects        : CRUD for detected defects
  - /api/roads          : CRUD for road master data
  - /api/dashboard      : Dashboard statistics
  - /api/reports        : Generate reports
"""

import os
import sys
import json
import hashlib
import shutil
import uuid
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text, func, desc, or_
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext

import models
import database

# Add AI models to Python path
AI_MODELS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai_models", "scripts"))
sys.path.insert(0, AI_MODELS_PATH)

# ===================== APP SETUP =====================

# Create the database tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Road AI Assessment API",
    description="AI-powered road defect detection and assessment system",
    version="2.0.0",
)

# CORS - allow dashboard to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploaded images
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "images"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "videos"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "annotated"), exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Serve dashbaord static files
DASHBOARD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dashboard"))
if os.path.exists(DASHBOARD_DIR):
    app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")


# ===================== PYDANTIC SCHEMAS =====================

class UserCreate(BaseModel):
    username: str
    password: str
    role: Optional[str] = "user" # admin, worker, user

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class WorkAssignment(BaseModel):
    issue_id: int
    worker_id: int
    notes: Optional[str] = None

class StatusUpdate(BaseModel):
    issue_id: int
    status: str # reported, assigned, in_progress, completed
    notes: Optional[str] = None

class DefectResponse(BaseModel):
    id: int
    road_name: Optional[str] = None
    defect_type: str
    severity: str
    confidence: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    estimated_area_sqm: Optional[float] = None
    repair_cost: float = 0.0
    repair_description: Optional[str] = None
    image_path: Optional[str] = None
    annotated_image_path: Optional[str] = None
    video_path: Optional[str] = None
    frame_number: Optional[int] = None
    time_seconds: Optional[float] = None
    polygon: Optional[list] = None
    timestamp: Optional[datetime] = None
    is_defect: bool = True

class SurveyCreate(BaseModel):
    road_name: str
    road_id: Optional[str] = None
    road_type: Optional[str] = None
    state: Optional[str] = None
    start_chainage: float = 0.0
    end_chainage: float = 0.0
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    surveyor_name: Optional[str] = None
    vehicle_id: Optional[str] = None

class RoadCreate(BaseModel):
    road_id: str
    road_name: str
    road_type: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    total_length_km: float = 0.0
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    end_latitude: Optional[float] = None
    end_longitude: Optional[float] = None

class DetectionRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    road_name: Optional[str] = None
    chainage: Optional[float] = None
    vibration_level: Optional[float] = None



# ===================== SECURITY SETUP =====================

SECRET_KEY = "ROAD_AI_PRODUCTION_SECRET_KEY_2025"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 1 week

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

# Create demo users if not exists
@app.on_event("startup")
def create_demo_users():
    db = database.SessionLocal()
    try:
        users_to_create = [
            {"username": "admin", "password": "admin123", "role": "admin"},
            {"username": "worker1", "password": "worker123", "role": "worker"},
            {"username": "user1", "password": "user123", "role": "user"},
        ]
        
        for user_data in users_to_create:
            existing = db.query(models.User).filter(models.User.username == user_data["username"]).first()
            if not existing:
                print(f"[INIT] Creating demo {user_data['role']} user ({user_data['username']} / {user_data['password']})...")
                from main import get_password_hash
                hashed_pw = get_password_hash(user_data["password"])
                new_user = models.User(
                    username=user_data["username"], 
                    password_hash=hashed_pw, 
                    role=user_data["role"]
                )
                db.add(new_user)
        
        db.commit()
    except Exception as e:
        print(f"[ERROR] Failed to create demo users: {e}")
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    if not token:
        return None
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

def require_role(allowed_roles: List[str]):
    async def role_checker(current_user: models.User = Depends(get_current_user)):
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{current_user.role}' is not authorized for this action"
            )
        return current_user
    return role_checker

# ===================== AUTH ENDPOINTS =====================

@app.post("/api/auth/register")
def register(user: UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_pwd = get_password_hash(user.password)
    new_user = models.User(username=user.username, password_hash=hashed_pwd, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "username": new_user.username, "role": new_user.role}

@app.post("/api/auth/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": db_user.username, "role": db_user.role})
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "role": db_user.role
    }

@app.get("/api/auth/me")
def get_me(current_user: models.User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role
    }

# ===================== HELPERS = ::::::::::::::::: =====================

def _parse_srt_gps(content: str) -> List[dict]:
    """Parse SRT subtitles to GPS list."""
    points = []
    # Simple regex to find blocks
    blocks = re.split(r'\n\s*\n', content.strip())
    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) < 3: continue
        
        # Line 2 is time
        time_match = re.search(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', lines[1])
        if not time_match: continue
        
        # Convert start time to seconds
        ts = time_match.group(1).replace(',', '.')
        h, m, s = map(float, ts.split(':'))
        time_sec = h * 3600 + m * 60 + s
        
        # Line 3 is coords: "Lat: X, Lng: Y" or similar
        # Support Lat, Lng, Longitude, etc.
        coord_match = re.search(r'Lat:\s*([-+]?\d*\.\d+|\d+).*?(?:Lng|Long|Longitude):\s*([-+]?\d*\.\d+|\d+)', lines[2], re.I)
        if coord_match:
            points.append({
                "time": time_sec,
                "latitude": float(coord_match.group(1)),
                "longitude": float(coord_match.group(2))
            })
    print(f"[INFO] Parsed SRT GPS: found {len(points)} points.")
    return points


@app.get("/")
def read_root():
    return {"message": "Road AI Assessment API v2.0", "status": "running"}


@app.get("/api/status")
def get_status(db: Session = Depends(database.get_db)):
    try:
        db.execute(text("SELECT 1"))
        total_defects = db.query(models.RoadDefect).count()
        total_surveys = db.query(models.Survey).count()
        total_roads = db.query(models.Road).count()
        
        return {
            "status": "healthy",
            "database": "connected",
            "total_defects": total_defects,
            "total_surveys": total_surveys,
            "total_roads": total_roads,
            "ai_model": "loaded" if _get_detector() else "not loaded",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ===================== PUBLIC ENDPOINTS =====================

@app.post("/api/report")
async def public_report(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    severity: str = Form("Medium"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db)
):
    """Anonymous or logged-in user reporting an issue."""
    file_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    save_path = os.path.join(UPLOAD_DIR, "images", f"report_{file_id}{ext}")
    
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    state = get_nearest_state(latitude, longitude)
    
    new_issue = models.RoadDefect(
        road_name="Public Report",
        latitude=latitude,
        longitude=longitude,
        state=state,
        defect_type="Reported Issue",
        severity=severity,
        image_path=save_path,
        status="reported",
        reported_by=current_user.id if current_user else None,
        is_defect=True
    )
    db.add(new_issue)
    db.commit()
    db.refresh(new_issue)
    return {"id": new_issue.id, "message": "Issue reported successfully"}

@app.get("/api/issues/map")
def get_issues_map(db: Session = Depends(database.get_db)):
    """Return all issues for map visualization."""
    issues = db.query(models.RoadDefect).filter(models.RoadDefect.is_defect == True).all()
    return [{
        "id": i.id,
        "lat": i.latitude,
        "lng": i.longitude,
        "type": i.defect_type,
        "severity": i.severity,
        "status": i.status
    } for i in issues]

# ===================== ADMIN ENDPOINTS =====================

@app.get("/api/admin/issues", dependencies=[Depends(require_role(["admin"]))])
def get_all_issues(db: Session = Depends(database.get_db)):
    return db.query(models.RoadDefect).all()

@app.post("/api/admin/assign-work", dependencies=[Depends(require_role(["admin"]))])
def assign_work(assignment: WorkAssignment, db: Session = Depends(database.get_db)):
    issue = db.query(models.RoadDefect).filter(models.RoadDefect.id == assignment.issue_id).first()
    worker = db.query(models.User).filter(models.User.id == assignment.worker_id, models.User.role == "worker").first()
    
    if not issue or not worker:
        raise HTTPException(status_code=404, detail="Issue or Worker not found")
    
    issue.status = "assigned"
    issue.assigned_to = worker.id
    
    new_order = models.WorkOrder(
        issue_id=issue.id,
        assigned_to=worker.id,
        status="assigned",
        admin_notes=assignment.notes
    )
    db.add(new_order)
    db.commit()
    return {"message": "Work assigned successfully", "issue_id": issue.id, "worker": worker.username}

@app.get("/api/admin/workers", dependencies=[Depends(require_role(["admin"]))])
def get_workers(db: Session = Depends(database.get_db)):
    return db.query(models.User).filter(models.User.role == "worker").all()

@app.get("/api/admin/analytics", dependencies=[Depends(require_role(["admin"]))])
def get_analytics(db: Session = Depends(database.get_db)):
    """Enhanced analytics for smart city platform."""
    # Defect distribution by state
    state_stats = db.query(models.RoadDefect.state, func.count(models.RoadDefect.id)).group_by(models.RoadDefect.state).all()
    # Severity trends
    severity_stats = db.query(models.RoadDefect.severity, func.count(models.RoadDefect.id)).group_by(models.RoadDefect.severity).all()
    # Status breakdown
    status_stats = db.query(models.RoadDefect.status, func.count(models.RoadDefect.id)).group_by(models.RoadDefect.status).all()
    
    return {
        "by_state": {s: c for s, c in state_stats},
        "by_severity": {s: c for s, c in severity_stats},
        "by_status": {s: c for s, c in status_stats}
    }

# ===================== WORKER ENDPOINTS =====================

@app.get("/api/worker/tasks", dependencies=[Depends(require_role(["worker"]))])
def get_worker_tasks(current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    tasks = db.query(models.RoadDefect).filter(models.RoadDefect.assigned_to == current_user.id).all()
    return tasks

@app.post("/api/worker/update-status", dependencies=[Depends(require_role(["worker", "admin"]))])
def update_task_status(update: StatusUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    issue = db.query(models.RoadDefect).filter(models.RoadDefect.id == update.issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Workers can only update their own tasks, admins can update any
    if current_user.role == "worker" and issue.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this task")
    
    issue.status = update.status
    if update.status == "completed":
        issue.is_resolved = True
        issue.resolved_at = datetime.utcnow()
        
    # Update work order too
    order = db.query(models.WorkOrder).filter(models.WorkOrder.issue_id == issue.id).order_by(desc(models.WorkOrder.created_at)).first()
    if order:
        order.status = update.status
        order.worker_notes = update.notes
        
    db.commit()
    return {"message": f"Status updated to {update.status}"}

# ===================== USER ENDPOINTS =====================

@app.get("/api/user/my-reports", dependencies=[Depends(require_role(["user"]))])
def get_my_reports(current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    return db.query(models.RoadDefect).filter(models.RoadDefect.reported_by == current_user.id).all()


# ===================== HELPER FUNCTIONS =====================

def get_nearest_state(lat: float, lng: float) -> str:
    states_coords = {
        "Andhra Pradesh": (15.9129, 79.7400), "Arunachal Pradesh": (28.2180, 94.7278),
        "Assam": (26.2006, 92.9376), "Bihar": (25.0961, 85.3131),
        "Chhattisgarh": (21.2787, 81.8661), "Goa": (15.2993, 74.1240),
        "Gujarat": (22.2587, 71.1924), "Haryana": (29.0588, 76.0856),
        "Himachal Pradesh": (31.1048, 77.1734), "Jharkhand": (23.6102, 85.2799),
        "Karnataka": (15.3173, 75.7139), "Kerala": (10.8505, 76.2711),
        "Madhya Pradesh": (22.9734, 78.6569), "Maharashtra": (19.7515, 75.7139),
        "Manipur": (24.6637, 93.9063), "Meghalaya": (25.4670, 91.3662),
        "Mizoram": (23.1645, 92.9376), "Nagaland": (26.1584, 94.5624),
        "Odisha": (20.9517, 85.0985), "Punjab": (31.1471, 75.3412),
        "Rajasthan": (27.0238, 74.2179), "Sikkim": (27.5330, 88.5122),
        "Tamil Nadu": (11.1271, 78.6569), "Telangana": (18.1124, 79.0193),
        "Tripura": (23.9408, 91.9882), "Uttar Pradesh": (26.8467, 80.9462),
        "Uttarakhand": (30.0668, 79.0193), "West Bengal": (22.9868, 87.8550),
        "Delhi": (28.7041, 77.1025), "Chandigarh": (30.7333, 76.7794),
        "Jammu and Kashmir": (33.7782, 76.5762), "Ladakh": (34.1526, 77.5771),
        "Puducherry": (11.9416, 79.8083), "Andaman and Nicobar Islands": (11.7401, 92.6586),
        "Lakshadweep": (10.5667, 72.6417), "Dadra and Nagar Haveli and Daman and Diu": (20.3974, 72.8328)
    }
    nearest_state = "Unknown"
    min_dist = float('inf')
    for s, (slat, slng) in states_coords.items():
        dist = ((lat - slat)**2 + (lng - slng)**2)**0.5
        if dist < min_dist:
            min_dist = dist
            nearest_state = s
    return nearest_state


# ===================== DETECTION ENDPOINTS =====================

def _get_detector():
    """Get the AI detector (lazy load with forced reload for development)."""
    try:
        import importlib
        import detection_service
        # Force reload to ensure AI logic updates (like removing Maharashtra fallback) are live
        importlib.reload(detection_service)
        return detection_service.get_detector()
    except Exception as e:
        print(f"[WARN] Detector and/or service failed: {e}")
        return None


@app.post("/api/detect")
async def detect_defects(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    road_name: Optional[str] = Form(None),
    chainage: Optional[float] = Form(None),
    survey_id: Optional[int] = Form(None),
    vibration_level: float = Form(0.0),
    save_results: bool = Form(True),
    db: Session = Depends(database.get_db)
):
    """Upload an image and detect road defects."""
    # Debug log for dashboard uploads
    print(f"[DEBUG] detect_defects called. save_results: {save_results} ({type(save_results)})")
    
    # Run manual conversion if needed (FastAPI sometimes receives strings)
    if isinstance(save_results, str):
        save_results = save_results.lower() not in ("false", "0", "no", "f")
    elif isinstance(save_results, int):
        save_results = bool(save_results)
    file_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    save_path = os.path.join(UPLOAD_DIR, "images", f"{file_id}{ext}")
    
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Run detection
    detector = _get_detector()
    if detector is None:
        raise HTTPException(status_code=503, detail="AI model not available")
    
    gps = None
    if latitude and longitude:
        gps = {"latitude": latitude, "longitude": longitude}
    
    result = detector.detect_image(save_path, gps)
    detections = result["detections"]
    orig_width = result["orig_width"]
    orig_height = result["orig_height"]
    
    print(f"[INFO] Detection complete: Found {len(detections)} items in {file.filename}")
    
    # Get annotated image
    temp_annotated_path = detector.get_annotated_image(save_path)
    annotated_path = None
    if temp_annotated_path and os.path.exists(temp_annotated_path):
        annotated_filename = os.path.basename(temp_annotated_path)
        final_annotated_path = os.path.join(UPLOAD_DIR, "annotated", annotated_filename)
        shutil.move(temp_annotated_path, final_annotated_path)
        annotated_path = final_annotated_path
        print(f"[INFO] Annotated image saved to: {annotated_path}")
    
    # Look up road metadata if road_name is provided
    road_obj = None
    if road_name:
        road_obj = db.query(models.Road).filter(
            (models.Road.road_name == road_name) | (models.Road.road_id == road_name)
        ).first()
    
    # Determine state from GPS if not found via road
    detected_state = road_obj.state if road_obj else None
    if not detected_state and latitude and longitude:
        detected_state = get_nearest_state(latitude, longitude)

    # Fetch survey object if doing inside a survey
    survey_obj = None
    if survey_id:
        survey_obj = db.query(models.Survey).filter(models.Survey.id == survey_id).first()
    saved_defects = []
    for d in detections:
        defect = models.RoadDefect(
            road_name=road_obj.road_name if road_obj else (road_name or "Unknown"),
            road_id=road_obj.road_id if road_obj else None,
            state=detected_state,
            chainage=chainage or 0.0,
            latitude=d.get("latitude", latitude),
            longitude=d.get("longitude", longitude),
            defect_type=d["class_name"],
            severity=d["severity"],
            confidence=d["confidence"],
            bbox_x1=d["bbox"]["x1"],
            bbox_y1=d["bbox"]["y1"],
            bbox_x2=d["bbox"]["x2"],
            bbox_y2=d["bbox"]["y2"],
            estimated_area_sqm=d.get("estimated_area_sqm", 0),
            repair_cost=d.get("repair_cost", {}).get("cost", 0),
            repair_description=d.get("repair_cost", {}).get("desc", ""),
            sor_rate_per_sqm=d.get("repair_cost", {}).get("rate_per_sqm", 0),
            image_path=save_path,
            annotated_image_path=annotated_path,
            vibration_level=vibration_level,
            is_defect=d.get("is_defect", True),
            survey_id=survey_id,
        )
        if save_results:
            db.add(defect)
        
        # Add the final public URL to the detection dict for frontend parity
        d["annotated_image_path"] = f"/uploads/annotated/{os.path.basename(annotated_path)}" if annotated_path else None
        saved_defects.append(defect)
        
        # update survey totals
        if save_results and survey_obj:
            survey_obj.total_defects += 1
            survey_obj.total_repair_cost += defect.repair_cost
    
    if save_results:
        db.commit()
    
    return {
        "file_id": file_id,
        "image_path": f"/uploads/images/{file_id}{ext}",
        "annotated_image": f"/uploads/annotated/{os.path.basename(annotated_path)}" if annotated_path else None,
        "total_detections": len(detections),
        "orig_width": orig_width,
        "orig_height": orig_height,
        "defects": detections,
    }


def _parse_srt_gps(srt_content: str) -> List[Dict]:
    """Parse GPS coordinates from SRT subtitles format."""
    if not srt_content:
        return []
    
    points = []
    # Split content by double newline (SRT standard)
    blocks = re.split(r'\n\s*\n', srt_content.strip())
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
            
        # Line 2 is timing: "00:00:00,000 --> 00:00:01,000"
        time_match = re.search(r'(\d{2}):(\d{2}):(\d{2})', lines[1])
        if not time_match:
            continue
            
        h, m, s = map(int, time_match.groups())
        time_sec = h * 3600 + m * 60 + s
        
        # Line 3 is coords: "Lat: X, Lng: Y" or similar
        # Support Lat, Lng, Longitude, etc. (case insensitive)
        coord_match = re.search(r'Lat:\s*([-+]?\d*\.\d+|\d+).*?(?:Lng|Long|Longitude):\s*([-+]?\d*\.\d+|\d+)', lines[2], re.I)
        
        if coord_match:
            points.append({
                "time": time_sec,
                "latitude": float(coord_match.group(1)),
                "longitude": float(coord_match.group(2))
            })
            
    print(f"[INFO] Parsed SRT GPS: found {len(points)} points.")
    return points



def _parse_gpx_gps(gpx_content: str) -> List[Dict]:
    """Parse GPS coordinates from standard GPX XML format."""
    if not gpx_content:
        return []
    
    points = []
    try:
        # Use regex to avoid dependency on xml libraries for simple parsing
        # Matches <trkpt lat="X" lon="Y"><time>Z</time></trkpt>
        import re
        from datetime import datetime
        
        # 1. Try to find the start time of the survey from metadata
        meta_time_match = re.search(r'<metadata>.*?<time>(.*?)</time>', gpx_content, re.S)
        start_time = None
        if meta_time_match:
            try:
                # Support various ISO formats
                t_str = meta_time_match.group(1).replace('Z', '+00:00')
                start_time = datetime.fromisoformat(t_str)
            except: pass

        # 2. Find all track points
        # Supports <trkpt lat="28.6" lon="77.2"><time>...</time></trkpt>
        pattern = r'<trkpt\s+lat="([-+]?\d*\.\d+|\d+)"\s+lon="([-+]?\d*\.\d+|\d+)">(.*?)</trkpt>'
        matches = re.finditer(pattern, gpx_content, re.S)
        
        for match in matches:
            lat = float(match.group(1))
            lon = float(match.group(2))
            inner = match.group(3)
            
            # Extract time
            time_val = 0.0
            t_match = re.search(r'<time>(.*?)</time>', inner)
            if t_match:
                try:
                    t_str = t_match.group(1).replace('Z', '+00:00')
                    curr_time = datetime.fromisoformat(t_str)
                    if start_time:
                        time_val = (curr_time - start_time).total_seconds()
                    else:
                        # Fallback: use absolute seconds if no start_time (less ideal)
                        time_val = curr_time.timestamp() % 86400 
                except: pass
            
            # Extract heading if available (extension)
            heading = None
            h_match = re.search(r'<heading>(.*?)</heading>', inner)
            if h_match:
                try: heading = float(h_match.group(1))
                except: pass
                
            points.append({
                "time": time_val,
                "latitude": lat,
                "longitude": lon,
                "heading": heading
            })
            
    except Exception as e:
        print(f"[ERROR] GPX parse failed: {e}")
        
    print(f"[INFO] Parsed GPX GPS: found {len(points)} points.")
    return points


@app.post("/api/detect/video")
async def detect_video(
    file: UploadFile = File(...),
    road_name: Optional[str] = Form(None),
    survey_id: Optional[int] = Form(None),
    frame_interval: int = Form(15),
    save_results: bool = Form(True),
    gps_data: Optional[str] = Form(None),
    db: Session = Depends(database.get_db)
):
    """Upload a video for batch defect detection."""
    # Debug log
    print(f"[DEBUG] detect_video called. save_results: {save_results} ({type(save_results)})")
    
    # Manual conversion
    if isinstance(save_results, str):
        save_results = save_results.lower() not in ("false", "0", "no", "f")
    elif isinstance(save_results, int):
        save_results = bool(save_results)
    
    import zipfile
    
    file_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(file.filename)[1].lower() or ".mp4"
    
    is_zip = ext == ".zip"
    video_save_path = None
    extracted_gps_data = gps_data
    
    if is_zip:
        zip_path = os.path.join(UPLOAD_DIR, "videos", f"{file_id}_bundle.zip")
        with open(zip_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        print(f"\n{'='*60}")
        print(f"[GPS-DEBUG] === ZIP UPLOAD PROCESSING START ===")
        print(f"[GPS-DEBUG] ZIP saved to: {zip_path} ({os.path.getsize(zip_path)} bytes)")
        print(f"[GPS-DEBUG] gps_data form field present: {gps_data is not None}")
        if gps_data:
            print(f"[GPS-DEBUG] gps_data form field length: {len(gps_data)} chars")
            print(f"[GPS-DEBUG] gps_data first 200 chars: {gps_data[:200]}")
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract to a temp folder
            temp_extract_dir = os.path.join(UPLOAD_DIR, f"temp_{file_id}")
            os.makedirs(temp_extract_dir, exist_ok=True)
            zip_ref.extractall(temp_extract_dir)
            
            zip_file_list = zip_ref.namelist()
            print(f"[GPS-DEBUG] ZIP contains {len(zip_file_list)} entries: {zip_file_list}")
            
            best_gps_content = None
            best_gps_score = -1
            best_gps_name = None
            all_found_files = []
            
            for root, dirs, files_in_dir in os.walk(temp_extract_dir):
                for f_name in files_in_dir:
                    # Skip macOS resource forks
                    if f_name.startswith('._') or f_name == '.DS_Store':
                        continue
                    
                    f_ext = os.path.splitext(f_name)[1].lower()
                    full_f_path = os.path.join(root, f_name)
                    
                    try:
                        f_size = os.path.getsize(full_f_path)
                    except:
                        f_size = 0
                    
                    rel_path = os.path.relpath(full_f_path, temp_extract_dir)
                    all_found_files.append((rel_path, f_ext, f_size))
                    print(f"[GPS-DEBUG] Found file: '{rel_path}' ext='{f_ext}' size={f_size}")
                    
                    # 1. Handle Video
                    if f_ext in [".mp4", ".avi", ".mov", ".mkv", ".3gp", ".webm"]:
                        if not video_save_path:
                            video_save_path = os.path.join(UPLOAD_DIR, "videos", f"{file_id}{f_ext}")
                            shutil.copy2(full_f_path, video_save_path)
                            print(f"[GPS-DEBUG] ✓ Video extracted: {f_name} -> {video_save_path}")
                        
                    # 2. Score potential GPS files (JSON/SRT)
                    if f_ext in [".json", ".srt", ".gpx"]:
                        score = 0
                        file_content = ""
                        try:
                            # Read with multiple encoding fallbacks
                            raw_bytes = open(full_f_path, 'rb').read()
                            
                            # Strip BOM (Byte Order Mark) if present
                            if raw_bytes.startswith(b'\xef\xbb\xbf'):
                                raw_bytes = raw_bytes[3:]
                                print(f"[GPS-DEBUG] Stripped UTF-8 BOM from '{f_name}'")
                            elif raw_bytes.startswith(b'\xff\xfe'):
                                raw_bytes = raw_bytes[2:]
                                print(f"[GPS-DEBUG] Stripped UTF-16 LE BOM from '{f_name}'")
                            elif raw_bytes.startswith(b'\xfe\xff'):
                                raw_bytes = raw_bytes[2:]
                                print(f"[GPS-DEBUG] Stripped UTF-16 BE BOM from '{f_name}'")
                            
                            # Try UTF-8 first, then latin-1 as fallback (never fails)
                            try:
                                file_content = raw_bytes.decode('utf-8')
                            except UnicodeDecodeError:
                                file_content = raw_bytes.decode('latin-1')
                                print(f"[GPS-DEBUG] Used latin-1 fallback for '{f_name}'")
                            
                            # Strip any invisible whitespace/null bytes
                            file_content = file_content.strip().strip('\x00')
                                
                            lower_name = f_name.lower()
                            lower_content = file_content.lower()
                            
                            print(f"[GPS-DEBUG] File '{f_name}': {len(file_content)} chars, first 300: {repr(file_content[:300])}")
                            
                            # Extension score
                            score += 5
                            
                            # Keyword score
                            if "gps" in lower_name: score += 20
                            if "track" in lower_name: score += 15
                            if "coord" in lower_name: score += 15
                            if f_ext == ".srt": score += 2 
                            if f_ext == ".gpx": score += 10 # GPX is preferred over SRT
                            if "meta" in lower_name and "gps" not in lower_name: score -= 10
                            
                            # Content score — check for GPS coordinates
                            has_lat = "latitude" in lower_content or '"lat"' in lower_content or "lat:" in lower_content
                            has_lon = "longitude" in lower_content or '"lng"' in lower_content or '"lon"' in lower_content or "lng:" in lower_content
                            if has_lat and has_lon: score += 50
                            
                            # SRT format detection
                            if "-->" in file_content and file_content.count('\n') > 2: score += 10
                            
                            # Direct JSON array with GPS — highest score boost
                            if f_ext == ".json" and file_content.lstrip().startswith('['):
                                try:
                                    test_parsed = json.loads(file_content)
                                    if isinstance(test_parsed, list) and len(test_parsed) > 0:
                                        first = test_parsed[0]
                                        if isinstance(first, dict) and ('latitude' in first or 'lat' in first):
                                            score += 30  # Verified GPS JSON
                                            print(f"[GPS-DEBUG] ✓ Verified GPS JSON: {len(test_parsed)} points, first={first}")
                                except:
                                    pass
                            
                            print(f"[GPS-DEBUG] Score for '{f_name}': {score} (has_lat={has_lat}, has_lon={has_lon})")
                            
                            if score > best_gps_score and score > 5:
                                best_gps_score = score
                                best_gps_content = file_content
                                best_gps_name = f_name
                        except Exception as e:
                            print(f"[GPS-DEBUG] ✗ Error reading/scoring '{f_name}': {e}")

            if best_gps_content:
                extracted_gps_data = best_gps_content
                print(f"[GPS-DEBUG] ✓ Best GPS File selected: '{best_gps_name}' (Score: {best_gps_score})")
                print(f"[GPS-DEBUG] GPS content length: {len(best_gps_content)} chars")
            else:
                print(f"[GPS-DEBUG] ✗ NO GPS file found in ZIP! Files scanned: {[f[0] for f in all_found_files]}")
            
            # Clean up temp dir
            try:
                import time
                time.sleep(0.1)
                shutil.rmtree(temp_extract_dir)
            except Exception as e:
                print(f"[WARN] Temp directory cleanup failed: {e}")
            
        # Clean up bundle after closing zip_ref
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except: pass
    else:
        video_save_path = os.path.join(UPLOAD_DIR, "videos", f"{file_id}{ext}")
        with open(video_save_path, "wb") as f:
            content = await file.read()
            f.write(content)
    
    if not video_save_path or not os.path.exists(video_save_path):
        raise HTTPException(status_code=400, detail="No valid video file found in upload")
    
    detector = _get_detector()
    if detector is None:
        raise HTTPException(status_code=503, detail="AI model not available")
    
    # === GPS PARSING ===
    parsed_gps = None
    print(f"[GPS-DEBUG] === GPS PARSING STAGE ===")
    print(f"[GPS-DEBUG] extracted_gps_data present: {extracted_gps_data is not None}")
    if extracted_gps_data:
        print(f"[GPS-DEBUG] extracted_gps_data length: {len(extracted_gps_data)}")
        
        # Strip BOM, null bytes, and whitespace
        data_str = extracted_gps_data.strip().strip('\x00').strip()
        
        # Strip UTF-8 BOM if still present as characters
        if data_str.startswith('\ufeff'):
            data_str = data_str[1:]
            print(f"[GPS-DEBUG] Stripped BOM character from GPS data")
        
        print(f"[GPS-DEBUG] data_str starts with: {repr(data_str[:50])}")
        
        # Try JSON parsing
        if data_str.startswith('[') or data_str.startswith('{'):
            try:
                parsed_gps = json.loads(data_str)
                # Handle { "points": [...] } wrapper
                if isinstance(parsed_gps, dict) and "points" in parsed_gps:
                    parsed_gps = parsed_gps["points"]
                
                if not isinstance(parsed_gps, list):
                    print(f"[GPS-DEBUG] ✗ GPS JSON is not a list: {type(parsed_gps)}")
                    parsed_gps = None
                elif len(parsed_gps) == 0:
                    print(f"[GPS-DEBUG] ✗ GPS JSON is empty list")
                    parsed_gps = None
                else:
                    # Normalize keys: support 'lat'/'lon' shorthand
                    normalized = []
                    for pt in parsed_gps:
                        if not isinstance(pt, dict):
                            continue
                        n_pt = {}
                        n_pt['latitude'] = pt.get('latitude', pt.get('lat'))
                        n_pt['longitude'] = pt.get('longitude', pt.get('lng', pt.get('lon')))
                        n_pt['time'] = pt.get('time', pt.get('timestamp', 0))
                        n_pt['heading'] = pt.get('heading')
                        
                        # Skip points with no valid coordinates
                        if n_pt['latitude'] is not None and n_pt['longitude'] is not None:
                            # Convert to float if string
                            try:
                                n_pt['latitude'] = float(n_pt['latitude'])
                                n_pt['longitude'] = float(n_pt['longitude'])
                                n_pt['time'] = float(n_pt['time'])
                            except (ValueError, TypeError):
                                continue
                            
                            # Basic sanity: valid GPS range
                            if -90 <= n_pt['latitude'] <= 90 and -180 <= n_pt['longitude'] <= 180:
                                normalized.append(n_pt)
                    
                    if normalized:
                        parsed_gps = normalized
                        print(f"[GPS-DEBUG] ✓ Parsed GPS JSON: {len(parsed_gps)} valid points")
                        print(f"[GPS-DEBUG] First point: {parsed_gps[0]}")
                        print(f"[GPS-DEBUG] Last point:  {parsed_gps[-1]}")
                    else:
                        print(f"[GPS-DEBUG] ✗ GPS JSON parsed but 0 valid coordinate points found")
                        parsed_gps = None
            except json.JSONDecodeError as e:
                print(f"[GPS-DEBUG] ✗ JSON parse failed: {e}")
                print(f"[GPS-DEBUG] Trying to clean and re-parse...")
                # Try cleaning common JSON issues (trailing commas, etc.)
                try:
                    clean = re.sub(r',\s*([\]\}])', r'\1', data_str)
                    parsed_gps = json.loads(clean)
                    if isinstance(parsed_gps, list) and len(parsed_gps) > 0:
                        print(f"[GPS-DEBUG] ✓ Cleaned JSON parse succeeded: {len(parsed_gps)} items")
                    else:
                        parsed_gps = None
                except:
                    parsed_gps = None
        
        # If JSON parsing didn't work, try SRT format
        if not parsed_gps:
            print(f"[GPS-DEBUG] Trying SRT parser...")
            try:
                parsed_gps = _parse_srt_gps(data_str)
                if parsed_gps:
                    print(f"[GPS-DEBUG] ✓ SRT parser found {len(parsed_gps)} GPS points")
                else:
                    print(f"[GPS-DEBUG] ✗ SRT parser returned 0 points")
            except Exception as e:
                print(f"[GPS-DEBUG] ✗ SRT parser failed: {e}")
        
        # If still no GPS, try GPX format
        if not parsed_gps:
            print(f"[GPS-DEBUG] Trying GPX parser...")
            try:
                parsed_gps = _parse_gpx_gps(data_str)
                if parsed_gps:
                    print(f"[GPS-DEBUG] ✓ GPX parser found {len(parsed_gps)} GPS points")
                else:
                    print(f"[GPS-DEBUG] ✗ GPX parser returned 0 points")
            except Exception as e:
                print(f"[GPS-DEBUG] ✗ GPX parser failed: {e}")
    else:
        print(f"[GPS-DEBUG] ✗ No GPS data available (neither form field nor ZIP extraction)")
    
    print(f"[GPS-DEBUG] === FINAL GPS RESULT: {len(parsed_gps) if parsed_gps else 0} points ===")
    print(f"{'='*60}\n")

    # Process video
    raw_results = detector.process_video(video_save_path, gps_data=parsed_gps, frame_interval=frame_interval)
    results = raw_results.get("detections", [])
    gps_count = len(parsed_gps) if parsed_gps else 0
    detections_count = len(results)
    
    video_filename = os.path.basename(video_save_path)
    video_public_path = f"/uploads/videos/{video_filename}"
    
    saved_defects = []
    
    # Save all detections
    for d in results:
        img_path = None
        annot_path = None
        
        temp_img = d.get("temp_image_path")
        if temp_img and os.path.exists(temp_img):
            new_img = os.path.join(UPLOAD_DIR, "images", os.path.basename(temp_img))
            if not os.path.exists(new_img):
                shutil.copy(temp_img, new_img)
            img_path = new_img
        
        temp_annot = d.get("temp_annot_path")
        if temp_annot and os.path.exists(temp_annot):
            new_annot = os.path.join(UPLOAD_DIR, "annotated", os.path.basename(temp_annot))
            if not os.path.exists(new_annot):
                shutil.copy(temp_annot, new_annot)
            annot_path = new_annot

        defect = models.RoadDefect(
            road_name=road_name or "Unknown",
            latitude=d.get("latitude"),
            longitude=d.get("longitude"),
            defect_type=d["class_name"],
            severity=d["severity"],
            confidence=d["confidence"],
            estimated_area_sqm=d.get("estimated_area_sqm", 0),
            repair_cost=d.get("repair_cost", {}).get("cost", 0),
            repair_description=d.get("repair_cost", {}).get("desc", ""),
            is_defect=d.get("is_defect", True),
            survey_id=survey_id,
            image_path=img_path,
            annotated_image_path=annot_path,
            video_path=video_public_path,
            frame_number=d.get("frame_number"),
            time_seconds=d.get("time_seconds"),
            polygon=d.get("polygon") or [
                [d.get("bbox", {}).get("x1", 0), d.get("bbox", {}).get("y1", 0)],
                [d.get("bbox", {}).get("x2", 0), d.get("bbox", {}).get("y1", 0)],
                [d.get("bbox", {}).get("x2", 0), d.get("bbox", {}).get("y2", 0)],
                [d.get("bbox", {}).get("x1", 0), d.get("bbox", {}).get("y2", 0)]
            ] if d.get("bbox") else None,
            bbox_x1=d.get("bbox", {}).get("x1"),
            bbox_y1=d.get("bbox", {}).get("y1"),
            bbox_x2=d.get("bbox", {}).get("x2"),
            bbox_y2=d.get("bbox", {}).get("y2")
        )
        if save_results:
            db.add(defect)
        saved_defects.append(defect)
    
    if save_results:
        db.commit()
    
    return {
        "file_id": file_id,
        "gps_points_count": gps_count,
        "detections_found": detections_count,
        "total_frames": raw_results.get("total_frames", 0),
        "frames_processed": raw_results.get("frames_processed", 0),
        "total_detections": raw_results.get("total_detections", 0),
        "total_defects": raw_results.get("total_defects", 0),
        "estimated_total_cost": raw_results.get("estimated_total_cost", 0),
        "defect_summary": raw_results.get("defect_summary", {}),
        "defects": [
            {
                "class_name": d.defect_type,
                "latitude": d.latitude,
                "longitude": d.longitude,
                "severity": d.severity,
                "confidence": d.confidence,
                "estimated_area_sqm": d.estimated_area_sqm,
                "annotated_image_path": f"/uploads/annotated/{os.path.basename(d.annotated_image_path)}" if d.annotated_image_path else None,
                "video_path": d.video_path,
                "frame_number": d.frame_number,
                "time_seconds": d.time_seconds,
                "polygon": d.polygon,
                "bbox": {"x1": d.bbox_x1, "y1": d.bbox_y1, "x2": d.bbox_x2, "y2": d.bbox_y2} if d.bbox_x1 is not None else None,
                "repair_cost": {
                    "cost": d.repair_cost,
                    "desc": d.repair_description
                }
            } for d in saved_defects
        ]
    }


# ===================== DEFECTS CRUD =====================

@app.get("/api/defects")
def get_defects(
    road_name: Optional[str] = None,
    defect_type: Optional[str] = None,
    severity: Optional[str] = None,
    survey_id: Optional[int] = None,
    is_defect: Optional[bool] = None,
    search: Optional[str] = None,
    video_path: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: Session = Depends(database.get_db)
):
    """Get all defects with optional filters."""
    query = db.query(models.RoadDefect)
    
    if road_name:
        query = query.filter(models.RoadDefect.road_name == road_name)
    if defect_type:
        query = query.filter(models.RoadDefect.defect_type == defect_type)
    if severity:
        query = query.filter(models.RoadDefect.severity == severity)
    if survey_id:
        query = query.filter(models.RoadDefect.survey_id == survey_id)
    if is_defect is not None:
        query = query.filter(models.RoadDefect.is_defect == is_defect)
    if search:
        query = query.filter((models.RoadDefect.road_name.ilike(f"%{search}%")) | (models.RoadDefect.defect_type.ilike(f"%{search}%")))
    if video_path:
        query = query.filter(models.RoadDefect.video_path == video_path)
        
    total = query.count()
    defects = query.order_by(desc(models.RoadDefect.timestamp)).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "defects": [
            {
                "id": d.id,
                "road_name": d.road_name,
                "road_id": d.road_id,
                "chainage": d.chainage,
                "latitude": d.latitude,
                "longitude": d.longitude,
                "defect_type": d.defect_type,
                "severity": d.severity,
                "confidence": d.confidence,
                "estimated_area_sqm": d.estimated_area_sqm,
                "repair_cost": d.repair_cost,
                "repair_description": d.repair_description,
                "image_path": f"/uploads/images/{os.path.basename(d.image_path)}" if d.image_path else None,
                "annotated_image_path": f"/uploads/annotated/{os.path.basename(d.annotated_image_path)}" if d.annotated_image_path else None,
                "video_path": d.video_path,
                "frame_number": d.frame_number,
                "time_seconds": d.time_seconds,
                "polygon": d.polygon,
                "bbox": {"x1": d.bbox_x1, "y1": d.bbox_y1, "x2": d.bbox_x2, "y2": d.bbox_y2} if d.bbox_x1 is not None else None,
                "is_defect": d.is_defect,
                "timestamp": d.timestamp.isoformat() if d.timestamp else None,
                "survey_id": d.survey_id,
            }
            for d in defects
        ]
    }


@app.get("/api/defects/map")
def get_defects_for_map(
    road_name: Optional[str] = None,
    road_type: Optional[str] = None,
    state: Optional[str] = None,
    severity: Optional[str] = None,
    defect_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(database.get_db)
):
    """Get defects with GPS data for map plotting with deep filters."""
    query = db.query(models.RoadDefect).filter(
        models.RoadDefect.latitude.isnot(None),
        models.RoadDefect.longitude.isnot(None),
        models.RoadDefect.is_defect == True,
        models.RoadDefect.is_resolved == False,
    )
    
    # Filters
    if state:
        query = query.filter(models.RoadDefect.state == state)
    if road_type:
        query = query.join(models.Road, models.RoadDefect.road_name == models.Road.road_name, isouter=True)
        query = query.filter(models.Road.road_type == road_type)
    if road_name:
        query = query.filter(models.RoadDefect.road_name == road_name)
    if severity:
        query = query.filter(models.RoadDefect.severity == severity)
    if defect_type:
        query = query.filter(models.RoadDefect.defect_type == defect_type)
    if search:
        query = query.filter((models.RoadDefect.road_name.ilike(f"%{search}%")) | (models.RoadDefect.defect_type.ilike(f"%{search}%")))
    
    defects = query.order_by(models.RoadDefect.timestamp.asc()).all()
    
    return [
        {
            "id": d.id,
            "defect_type": d.defect_type,
            "severity": d.severity,
            "confidence": d.confidence,
            "repair_cost": d.repair_cost,
            "repair_description": d.repair_description,
            "road_name": d.road_name,
            "latitude": d.latitude,
            "longitude": d.longitude,
            "estimated_area_sqm": d.estimated_area_sqm,
            "image_path": f"/uploads/images/{os.path.basename(d.image_path)}" if d.image_path else None,
            "annotated_image_path": f"/uploads/annotated/{os.path.basename(d.annotated_image_path)}" if d.annotated_image_path else None,
            "timestamp": d.timestamp.isoformat() if d.timestamp else None,
        }
        for d in defects
    ]


@app.get("/api/defects/{defect_id}")
def get_defect(defect_id: int, db: Session = Depends(database.get_db)):
    """Get a single defect by ID."""
    defect = db.query(models.RoadDefect).filter(models.RoadDefect.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    return defect



# ===================== SURVEYS CRUD =====================

@app.post("/api/surveys")
def create_survey(survey: SurveyCreate, db: Session = Depends(database.get_db)):
    """Create a new road survey."""
    # Auto-fill road_id if missing but road_name provided
    road_id = survey.road_id
    road_state = survey.state
    if not road_id and survey.road_name:
        road_obj = db.query(models.Road).filter(models.Road.road_name == survey.road_name).first()
        if road_obj:
            road_id = road_obj.road_id
            if not road_state:
                road_state = road_obj.state

    if not road_state and survey.start_latitude and survey.start_longitude:
        road_state = get_nearest_state(survey.start_latitude, survey.start_longitude)

    new_survey = models.Survey(
        road_name=survey.road_name,
        road_id=road_id,
        road_type=survey.road_type,
        state=road_state,
        start_chainage=survey.start_chainage,
        end_chainage=survey.end_chainage,
        start_latitude=survey.start_latitude,
        start_longitude=survey.start_longitude,
        surveyor_name=survey.surveyor_name,
        vehicle_id=survey.vehicle_id,
    )
    db.add(new_survey)
    db.commit()
    db.refresh(new_survey)
    return {"id": new_survey.id, "status": "created"}


@app.get("/api/surveys")
def get_surveys(
    road_name: Optional[str] = None,
    status: Optional[str] = None,
    state: Optional[str] = None,
    road_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(database.get_db)
):
    """Get all surveys."""
    query = db.query(models.Survey)
    if road_name:
        query = query.filter(models.Survey.road_name == road_name)
    if status:
        query = query.filter(models.Survey.status == status)
    if state:
        query = query.filter(models.Survey.state == state)
    if road_type:
        query = query.filter(models.Survey.road_type == road_type)
    if search:
        query = query.filter((models.Survey.road_name.ilike(f"%{search}%")) | (models.Survey.surveyor_name.ilike(f"%{search}%")))
    
    surveys = query.order_by(desc(models.Survey.created_at)).limit(limit).all()
    
    # Build repair status lookup: road_name -> latest RepairRecord
    road_names = list(set(s.road_name for s in surveys if s.road_name))
    repair_map = {}
    if road_names:
        repair_records = db.query(models.RepairRecord).filter(
            models.RepairRecord.road_name.in_(road_names)
        ).order_by(desc(models.RepairRecord.created_at)).all()
        
        for r in repair_records:
            key = (r.road_name, r.survey_id)
            if key not in repair_map:
                repair_map[key] = r
            # Also store by road_name only (fallback)
            if r.road_name not in repair_map:
                repair_map[r.road_name] = r
    
    result_surveys = []
    for s in surveys:
        # Find repair record: prefer exact match (road_name + survey_id), fallback to road_name only
        repair = repair_map.get((s.road_name, s.id)) or repair_map.get(s.road_name)
        
        result_surveys.append({
            "id": s.id,
            "road_name": s.road_name,
            "road_id": s.road_id,
            "road_type": s.road_type,
            "state": s.state,
            "start_chainage": s.start_chainage,
            "end_chainage": s.end_chainage,
            "total_length_km": s.total_length_km,
            "surveyor_name": s.surveyor_name,
            "total_defects": len(s.defects) if s.defects else 0,
            "total_repair_cost": sum([d.repair_cost for d in s.defects]) if s.defects else 0,
            "road_condition": s.road_condition,
            "pci_score": s.pci_score,
            "status": s.status,
            "survey_date": s.survey_date.isoformat() if s.survey_date else None,
            "repair_status": repair.status if repair else None,
            "repair_admin_notes": repair.admin_notes if repair else None,
        })
    
    return {"surveys": result_surveys}


@app.get("/api/surveys/{survey_id}")
def get_survey(survey_id: int, db: Session = Depends(database.get_db)):
    """Get a single survey with its defects."""
    survey = db.query(models.Survey).filter(models.Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    defects = db.query(models.RoadDefect).filter(
        models.RoadDefect.survey_id == survey_id
    ).all()
    
    return {
        "survey": {
            "id": survey.id,
            "road_name": survey.road_name,
            "road_id": survey.road_id,
            "start_chainage": survey.start_chainage,
            "end_chainage": survey.end_chainage,
            "total_defects": len(defects),
            "total_repair_cost": sum([d.repair_cost for d in defects]),
            "road_condition": survey.road_condition,
            "pci_score": survey.pci_score,
            "status": survey.status,
        },
        "defects": [
            {
                "id": d.id,
                "defect_type": d.defect_type,
                "severity": d.severity,
                "confidence": d.confidence,
                "latitude": d.latitude,
                "longitude": d.longitude,
                "repair_cost": d.repair_cost,
                "chainage": d.chainage,
                "image_path": f"/uploads/images/{os.path.basename(d.image_path)}" if d.image_path else None,
                "annotated_image_path": f"/uploads/annotated/{os.path.basename(d.annotated_image_path)}" if d.annotated_image_path else None,
            }
            for d in defects
        ],
    }


@app.patch("/api/surveys/{survey_id}/status")
def update_survey_status(survey_id: int, status: str = Query(...), db: Session = Depends(database.get_db)):
    """Update the status of a road survey."""
    survey = db.query(models.Survey).filter(models.Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    survey.status = status
    db.commit()
    db.refresh(survey)
    return {"id": survey.id, "status": survey.status}


# ===================== ROADS CRUD =====================

@app.post("/api/roads")
def create_road(road: RoadCreate, db: Session = Depends(database.get_db)):
    """Create a new road record."""
    existing = db.query(models.Road).filter(models.Road.road_id == road.road_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Road {road.road_id} already exists")
    
    new_road = models.Road(**road.dict())
    db.add(new_road)
    db.commit()
    db.refresh(new_road)
    return {"id": new_road.id, "road_id": new_road.road_id, "status": "created"}


@app.get("/api/roads")
def get_roads(
    state: Optional[str] = None,
    road_type: Optional[str] = None,
    search: Optional[str] = None, 
    db: Session = Depends(database.get_db)
):
    """Get all roads."""
    query = db.query(models.Road)
    if state:
        query = query.filter(models.Road.state == state)
    if road_type:
        query = query.filter(models.Road.road_type == road_type)
    if search:
        query = query.filter(models.Road.road_name.ilike(f"%{search}%"))
    roads = query.all()
    return {
        "roads": [
            {
                "id": r.id,
                "road_id": r.road_id,
                "road_name": r.road_name,
                "road_type": r.road_type,
                "district": r.district,
                "total_length_km": r.total_length_km,
                "overall_condition": r.overall_condition,
                "pci_score": r.pci_score,
                "last_survey_date": r.last_survey_date.isoformat() if r.last_survey_date else None,
            }
            for r in roads
        ]
    }

# ===================== REPAIRS CRUD =====================

class RepairCreate(BaseModel):
    road_name: str
    survey_id: Optional[int] = None
    surveyor_name: Optional[str] = None

@app.post("/api/repairs")
def create_repair(repair: RepairCreate, db: Session = Depends(database.get_db)):
    """Surveyor marks a road as repaired."""
    new_repair = models.RepairRecord(
        road_name=repair.road_name,
        survey_id=repair.survey_id,
        surveyor_name=repair.surveyor_name,
        status="pending",
    )
    db.add(new_repair)
    db.commit()
    db.refresh(new_repair)
    return {"id": new_repair.id, "status": "pending", "message": "Repair record created. Pending admin approval."}

@app.get("/api/repairs")
def get_repairs(
    status: Optional[str] = None,
    road_name: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(database.get_db)
):
    """Get all repair records with optional filters."""
    query = db.query(models.RepairRecord)
    if status:
        query = query.filter(models.RepairRecord.status == status)
    if road_name:
        query = query.filter(models.RepairRecord.road_name.ilike(f"%{road_name}%"))
    
    repairs = query.order_by(desc(models.RepairRecord.created_at)).limit(limit).all()
    
    result = []
    for r in repairs:
        # Count defects linked to this road
        defect_count = db.query(models.RoadDefect).filter(
            models.RoadDefect.road_name == r.road_name,
            models.RoadDefect.is_defect == True,
            models.RoadDefect.is_resolved == False,
        ).count()
        
        total_cost = db.query(func.sum(models.RoadDefect.repair_cost)).filter(
            models.RoadDefect.road_name == r.road_name,
            models.RoadDefect.is_defect == True,
            models.RoadDefect.is_resolved == False,
        ).scalar() or 0
        
        result.append({
            "id": r.id,
            "road_name": r.road_name,
            "survey_id": r.survey_id,
            "surveyor_name": r.surveyor_name,
            "repair_date": r.repair_date.isoformat() if r.repair_date else None,
            "status": r.status,
            "admin_notes": r.admin_notes,
            "defects_resolved": r.defects_resolved,
            "cost_saved": r.cost_saved,
            "pending_defects": defect_count,
            "pending_cost": float(total_cost),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    
    return {"repairs": result}

@app.patch("/api/repairs/{repair_id}/approve")
def approve_repair(repair_id: int, db: Session = Depends(database.get_db)):
    """Admin approves a repair — resolves all defects for that road."""
    repair = db.query(models.RepairRecord).filter(models.RepairRecord.id == repair_id).first()
    if not repair:
        raise HTTPException(status_code=404, detail="Repair record not found")
    if repair.status == "approved":
        raise HTTPException(status_code=400, detail="Repair already approved")
    
    # Find all unresolved defects for this road
    defects = db.query(models.RoadDefect).filter(
        models.RoadDefect.road_name == repair.road_name,
        models.RoadDefect.is_defect == True,
        models.RoadDefect.is_resolved == False,
    ).all()
    
    resolved_count = len(defects)
    cost_saved = sum(d.repair_cost or 0 for d in defects)
    
    # Mark all defects as resolved
    for d in defects:
        d.is_resolved = True
        d.resolved_at = datetime.utcnow()
    
    # Update repair record
    repair.status = "approved"
    repair.defects_resolved = resolved_count
    repair.cost_saved = round(cost_saved, 2)
    repair.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "id": repair.id,
        "status": "approved",
        "defects_resolved": resolved_count,
        "cost_saved": round(cost_saved, 2),
        "message": f"Approved! {resolved_count} defects resolved, ₹{round(cost_saved, 2)} cost saved."
    }

@app.patch("/api/repairs/{repair_id}/reject")
def reject_repair(repair_id: int, notes: str = Query(""), db: Session = Depends(database.get_db)):
    """Admin rejects a repair."""
    repair = db.query(models.RepairRecord).filter(models.RepairRecord.id == repair_id).first()
    if not repair:
        raise HTTPException(status_code=404, detail="Repair record not found")
    
    repair.status = "rejected"
    repair.admin_notes = notes
    repair.updated_at = datetime.utcnow()
    db.commit()
    
    return {"id": repair.id, "status": "rejected", "message": "Repair rejected."}


# ===================== DASHBOARD STATISTICS =====================

@app.get("/api/status")
def get_status():
    """System health check."""
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/api/dashboard/stats")
def get_dashboard_stats(
    state: Optional[str] = None,
    road_type: Optional[str] = None,
    road_name: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(database.get_db)
):
    """Get comprehensive dashboard statistics with filters."""
    # Defect query with filters — exclude resolved defects
    defect_query = db.query(models.RoadDefect).filter(
        models.RoadDefect.is_defect == True,
        models.RoadDefect.is_resolved == False,
    )
    
    # Filters
    if state:
        defect_query = defect_query.filter(models.RoadDefect.state == state)
    if road_type:
        defect_query = defect_query.join(models.Road, models.RoadDefect.road_name == models.Road.road_name, isouter=True)
        defect_query = defect_query.filter(models.Road.road_type == road_type)
    if road_name:
        defect_query = defect_query.filter(models.RoadDefect.road_name == road_name)
    if search:
        defect_query = defect_query.filter((models.RoadDefect.road_name.ilike(f"%{search}%")) | (models.RoadDefect.defect_type.ilike(f"%{search}%")))
    
    total_defects = defect_query.count()
    
    # Total cost with filters
    total_cost_query = db.query(func.sum(models.RoadDefect.repair_cost)).filter(
        models.RoadDefect.is_defect == True,
        models.RoadDefect.is_resolved == False,
    )
    if state:
        total_cost_query = total_cost_query.filter(models.RoadDefect.state == state)
    if road_type:
        total_cost_query = total_cost_query.join(models.Road, models.RoadDefect.road_name == models.Road.road_name, isouter=True)
        total_cost_query = total_cost_query.filter(models.Road.road_type == road_type)
    if road_name:
        total_cost_query = total_cost_query.filter(models.RoadDefect.road_name == road_name)
    if search:
        total_cost_query = total_cost_query.filter((models.RoadDefect.road_name.ilike(f"%{search}%")) | (models.RoadDefect.defect_type.ilike(f"%{search}%")))
        
    total_cost_result = total_cost_query.scalar()
    total_cost = float(total_cost_result) if total_cost_result else 0
    
    # Severity distribution
    severity_query = db.query(
        models.RoadDefect.severity,
        func.count(models.RoadDefect.id).label('count')
    ).filter(
        models.RoadDefect.is_defect == True,
        models.RoadDefect.is_resolved == False,
    )
    
    if state or road_type:
        severity_query = severity_query.join(models.Road, models.RoadDefect.road_name == models.Road.road_name, isouter=True)
        if state: severity_query = severity_query.filter(models.Road.state == state)
        if road_type: severity_query = severity_query.filter(models.Road.road_type == road_type)
    if road_name:
        severity_query = severity_query.filter(models.RoadDefect.road_name == road_name)
    if search:
        severity_query = severity_query.filter((models.RoadDefect.road_name.ilike(f"%{search}%")) | (models.RoadDefect.defect_type.ilike(f"%{search}%")))
    
    severity_distribution = severity_query.group_by(models.RoadDefect.severity).all()
    
    # Defect type distribution with cost
    type_query = db.query(
        models.RoadDefect.defect_type,
        func.count(models.RoadDefect.id).label('count'),
        func.sum(models.RoadDefect.repair_cost).label('total_cost')
    ).filter(
        models.RoadDefect.is_defect == True,
        models.RoadDefect.is_resolved == False,
    )
    
    if state or road_type:
        type_query = type_query.join(models.Road, models.RoadDefect.road_name == models.Road.road_name, isouter=True)
        if state: type_query = type_query.filter(models.Road.state == state)
        if road_type: type_query = type_query.filter(models.Road.road_type == road_type)
    if road_name:
        type_query = type_query.filter(models.RoadDefect.road_name == road_name)
    if search:
        type_query = type_query.filter((models.RoadDefect.road_name.ilike(f"%{search}%")) | (models.RoadDefect.defect_type.ilike(f"%{search}%")))
        
    type_distribution = type_query.group_by(models.RoadDefect.defect_type).all()

    # Top affected roads
    roads_query = db.query(
        models.RoadDefect.road_name,
        func.count(models.RoadDefect.id).label('defect_count'),
        func.sum(models.RoadDefect.repair_cost).label('total_cost')
    ).filter(
        models.RoadDefect.is_defect == True,
        models.RoadDefect.is_resolved == False,
    )
    
    if state or road_type:
        roads_query = roads_query.join(models.Road, models.RoadDefect.road_name == models.Road.road_name, isouter=True)
        if state: roads_query = roads_query.filter(models.Road.state == state)
        if road_type: roads_query = roads_query.filter(models.Road.road_type == road_type)
    if search:
        roads_query = roads_query.filter((models.RoadDefect.road_name.ilike(f"%{search}%")) | (models.RoadDefect.defect_type.ilike(f"%{search}%")))
        
    top_roads = roads_query.group_by(models.RoadDefect.road_name).order_by(desc('defect_count')).limit(5).all()

    # Repaired roads
    repaired_query = db.query(
        models.RoadDefect.road_name,
        func.count(models.RoadDefect.id).label('repair_count'),
        func.sum(models.RoadDefect.repair_cost).label('total_cost')
    ).filter(models.RoadDefect.defect_type.ilike('%repair%'))
    
    if state or road_type:
        repaired_query = repaired_query.join(models.Road, models.RoadDefect.road_name == models.Road.road_name, isouter=True)
        if state: repaired_query = repaired_query.filter(models.Road.state == state)
        if road_type: repaired_query = repaired_query.filter(models.Road.road_type == road_type)
    if search:
        repaired_query = repaired_query.filter((models.RoadDefect.road_name.ilike(f"%{search}%")) | (models.RoadDefect.defect_type.ilike(f"%{search}%")))
        
    top_repaired = repaired_query.group_by(models.RoadDefect.road_name).order_by(desc('repair_count')).limit(5).all()

    # Recent activity (last 5 detections)
    recent_activity = defect_query.order_by(desc(models.RoadDefect.timestamp)).limit(5).all()
    
    # Total surveys and roads with filters
    surveys_query = db.query(models.Survey)
    roads_filter_query = db.query(models.Road)
    
    if state:
        surveys_query = surveys_query.filter(models.Survey.state == state)
        roads_filter_query = roads_filter_query.filter(models.Road.state == state)
    if road_type:
        surveys_query = surveys_query.filter(models.Survey.road_type == road_type)
        roads_filter_query = roads_filter_query.filter(models.Road.road_type == road_type)
        
    total_surveys = surveys_query.count()
    total_roads = roads_filter_query.count()
    
    return {
        "total_defects": total_defects,
        "total_surveys": total_surveys,
        "total_roads": total_roads,
        "total_repair_cost": total_cost,
        "severity_distribution": [{"severity": s.severity, "count": s.count} for s in severity_distribution],
        "defect_type_distribution": [{"type": t.defect_type, "count": t.count, "total_cost": float(t.total_cost or 0)} for t in type_distribution],
        "top_affected_roads": [{"road_name": r.road_name, "defect_count": r.defect_count, "total_cost": float(r.total_cost or 0)} for r in top_roads],
        "top_repaired_roads": [{"road_name": r.road_name, "repair_count": r.repair_count, "total_cost": float(r.total_cost or 0)} for r in top_repaired],
        "recent_activity": [
            {
                "id": d.id,
                "road_name": d.road_name,
                "type": d.defect_type,
                "severity": d.severity,
                "image_path": f"/uploads/images/{os.path.basename(d.image_path)}" if d.image_path else None,
                "annotated_image_path": f"/uploads/annotated/{os.path.basename(d.annotated_image_path)}" if d.annotated_image_path else None,
                "timestamp": d.timestamp.isoformat()
            }
            for d in recent_activity
        ]
    }

@app.get("/api/filters/values")
def get_filter_values(db: Session = Depends(database.get_db)):
    """Get unique values for filters."""
    # List of unique states
    states = db.query(models.Road.state).filter(models.Road.state.isnot(None)).distinct().all()
    # List of unique road types
    road_types = db.query(models.Road.road_type).filter(models.Road.road_type.isnot(None)).distinct().all()
    # List of unique defect types
    defect_types = db.query(models.RoadDefect.defect_type).distinct().all()
    
    return {
        "states": [s[0] for s in states if s[0]],
        "road_types": [r[0] for r in road_types if r[0]],
        "defect_types": [d[0] for d in defect_types if d[0]]
    }

# ===================== SURVEYS =====================



@app.get("/api/dashboard/trends")
def get_trends(
    days: int = 30,
    state: Optional[str] = None,
    road_type: Optional[str] = None,
    road_name: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(database.get_db)
):
    """Get defect detection trends over time with full filtering support."""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Base query
    query = db.query(models.RoadDefect).filter(
        models.RoadDefect.is_defect == True,
        models.RoadDefect.timestamp >= start_date
    )
    
    # Apply filters (consistent with global dashboard filters)
    if state:
        query = query.filter(models.RoadDefect.state == state)
    if road_type:
        query = query.join(models.Road, models.RoadDefect.road_name == models.Road.road_name, isouter=True)
        query = query.filter(models.Road.road_type == road_type)
    if road_name:
        query = query.filter(models.RoadDefect.road_name == road_name)
    if search:
        query = query.filter((models.RoadDefect.road_name.ilike(f"%{search}%")) | (models.RoadDefect.defect_type.ilike(f"%{search}%")))
    
    defects = query.all()
    
    # Group by date
    daily_counts = {}
    for d in defects:
        if not d.timestamp: continue
        date_str = d.timestamp.strftime("%Y-%m-%d")
        if date_str not in daily_counts:
            daily_counts[date_str] = {"count": 0, "cost": 0}
        daily_counts[date_str]["count"] += 1
        daily_counts[date_str]["cost"] += (d.repair_cost or 0)
    
    return {
        "period_days": days,
        "total_in_period": len(defects),
        "daily_data": [
            {"date": date, "count": data["count"], "cost": round(data["cost"], 2)}
            for date, data in sorted(daily_counts.items())
        ]
    }


# ===================== REPORTS =====================

@app.get("/api/reports/summary")
def generate_summary_report(
    road_name: Optional[str] = None,
    road_type: Optional[str] = None,
    state: Optional[str] = None,
    search: Optional[str] = None,
    survey_id: Optional[int] = None,
    db: Session = Depends(database.get_db)
):
    """Generate a comprehensive summary report."""
    from sqlalchemy import and_, or_
    
    # Use outer join with precise match on road name AND state to prevent duplicates
    query = db.query(models.RoadDefect).outerjoin(
        models.Road, 
        and_(
            models.RoadDefect.road_name == models.Road.road_name,
            models.RoadDefect.state == models.Road.state
        )
    ).filter(models.RoadDefect.is_defect == True)
    
    if road_name:
        query = query.filter(models.RoadDefect.road_name == road_name)
    
    if search:
        query = query.filter(or_(
            models.RoadDefect.road_name.ilike(f"%{search}%"),
            models.RoadDefect.defect_type.ilike(f"%{search}%")
        ))
    
    if state:
        # Strict state filter on the defect itself
        query = query.filter(models.RoadDefect.state.ilike(state))
        
    if road_type:
        query = query.filter(models.Road.road_type == road_type)
        
    if survey_id:
        query = query.filter(models.RoadDefect.survey_id == survey_id)
    
    defects = query.all()
    
    if not defects:
        # If no defects found for specific filters, let the user know
        msg = "No defects found"
        if state: msg += f" in {state}"
        if road_type: msg += f" for {road_type} roads"
        return {"message": f"{msg}. Please ensure data has been scanned and uploaded."}
    
    # Calculate overall condition
    total = len(defects)
    high_count = sum(1 for d in defects if d.severity == "High")
    med_count = sum(1 for d in defects if d.severity == "Medium")
    
    overall_condition = "Good"
    if total > 0:
        if high_count / total > 0.1 or high_count > 5:
            overall_condition = "Bad"
        elif med_count / total > 0.2:
            overall_condition = "Average"

    # Build report
    report = {
        "report_title": f"Road Defect Assessment Report",
        "generated_at": datetime.utcnow().isoformat(),
        "road_name": road_name or "All Roads",
        "total_defects": total,
        "total_repair_cost": round(sum(d.repair_cost or 0 for d in defects), 2),
        "overall_condition": overall_condition,
        "defect_breakdown": {},
        "severity_summary": {"Low": 0, "Medium": 0, "High": 0},
        "cost_by_type": {},
        "recommendations": [],
    }
    
    for d in defects:
        # Type breakdown
        if d.defect_type not in report["defect_breakdown"]:
            report["defect_breakdown"][d.defect_type] = {
                "count": 0, "cost": 0,
                "severities": {"Low": 0, "Medium": 0, "High": 0}
            }
        report["defect_breakdown"][d.defect_type]["count"] += 1
        report["defect_breakdown"][d.defect_type]["cost"] += d.repair_cost or 0
        
        if d.severity in report["severity_summary"]:
            report["severity_summary"][d.severity] += 1
        
        if d.severity in report["defect_breakdown"][d.defect_type]["severities"]:
            report["defect_breakdown"][d.defect_type]["severities"][d.severity] += 1
    
    # Generate recommendations
    high_count = report["severity_summary"]["High"]
    if high_count > 0:
        report["recommendations"].append(
            f"URGENT: {high_count} high-severity defects require immediate attention."
        )
    
    # Find most common defect
    most_common = max(report["defect_breakdown"].items(), key=lambda x: x[1]["count"])
    report["recommendations"].append(
        f"Most common defect: {most_common[0]} ({most_common[1]['count']} instances). "
        f"Consider preventive maintenance program."
    )
    
    # Calculate road condition
    if len(defects) < 5:
        report["overall_condition"] = "Good"
    elif report["severity_summary"]["High"] > 3:
        report["overall_condition"] = "Bad"
    elif report["severity_summary"]["Medium"] > len(defects) * 0.3:
        report["overall_condition"] = "Average"
    else:
        report["overall_condition"] = "Good"
    
    return report


# ===================== SEED DATA (For Dashboard Demo) =====================

@app.post("/api/seed-demo-data")
def seed_demo_data(db: Session = Depends(database.get_db)):
    """Seed the database with demo data for dashboard visualization."""
    import random
    
    # Demo roads across different states
    demo_roads = [
        {"road_id": "MDR-0", "road_name": "Market Road", "road_type": "MDR", 
         "district": "Gandhinagar", "state": "Gujarat", "total_length_km": 12.5,
         "start_latitude": 23.2156, "start_longitude": 72.6369,
         "end_latitude": 23.2320, "end_longitude": 72.6580},
        {"road_id": "MDR-22", "road_name": "Industrial Highway", "road_type": "MDR",
         "district": "Ahmedabad", "state": "Gujarat", "total_length_km": 28.3,
         "start_latitude": 23.0225, "start_longitude": 72.5714,
         "end_latitude": 23.0650, "end_longitude": 72.6200},
        {"road_id": "SH-5", "road_name": "Western Express", "road_type": "SH",
         "district": "Mumbai", "state": "Maharashtra", "total_length_km": 45.0,
         "start_latitude": 19.0760, "start_longitude": 72.8777,
         "end_latitude": 19.1200, "end_longitude": 72.9200},
        {"road_id": "NH-48", "road_name": "Outer Ring Road", "road_type": "NH",
         "district": "New Delhi", "state": "Delhi", "total_length_km": 120.0,
         "start_latitude": 28.6139, "start_longitude": 77.2090,
         "end_latitude": 28.7000, "end_longitude": 77.3000},
        {"road_id": "VR-12", "road_name": "Village Road 12", "road_type": "VR",
         "district": "Mehsana", "state": "Gujarat", "total_length_km": 8.0,
         "start_latitude": 23.5880, "start_longitude": 72.3693,
         "end_latitude": 23.6000, "end_longitude": 72.3800},
    ]
    
    for rd in demo_roads:
        existing = db.query(models.Road).filter(models.Road.road_id == rd["road_id"]).first()
        if not existing:
            db.add(models.Road(**rd))
    
    # Demo defect types and severities
    defect_types = [
        "Pothole", "Edge_Deterioration", "Alligator_Cracking", "Rutting",
        "Subsidence", "Cracking", "Bleeding", "Fretting", "Repaired_Pothole"
    ]
    severities = ["Low", "Medium", "High"]
    conditions = ["Good", "Average", "Bad"]
    
    # Create demo surveys and defects
    for road in demo_roads:
        # Create 2-3 surveys per road
        for s_idx in range(random.randint(2, 3)):
            survey = models.Survey(
                road_name=road["road_name"],
                road_id=road["road_id"],
                state=road["state"],
                road_type=road["road_type"],
                start_chainage=0,
                end_chainage=road["total_length_km"] * 1000,
                total_length_km=road["total_length_km"],
                surveyor_name=random.choice(["Raj Kumar", "Amit Patel", "Priya Shah", "Suresh Modi"]),
                vehicle_id=f"IND-{random.randint(1,28):02d}-{random.choice('ABCDEFGH')}{random.choice('ABCDEFGH')}-{random.randint(1000,9999)}",
                survey_date=datetime.utcnow() - timedelta(days=random.randint(1, 90)),
                total_defects=0,
                total_repair_cost=0.0,
                road_condition=random.choice(conditions),
                pci_score=random.uniform(40, 95),
                status="completed",
                start_latitude=road["start_latitude"],
                start_longitude=road["start_longitude"],
                end_latitude=road["end_latitude"],
                end_longitude=road["end_longitude"],
            )
            db.add(survey)
            db.flush()
            
            # Create 5-30 defects per survey
            n_defects = random.randint(5, 30)
            total_cost = 0
            
            for d_idx in range(n_defects):
                lat = road["start_latitude"] + random.uniform(0, road["end_latitude"] - road["start_latitude"])
                lon = road["start_longitude"] + random.uniform(0, road["end_longitude"] - road["start_longitude"])
                
                defect_type = random.choice(defect_types)
                severity = random.choices(severities, weights=[0.4, 0.35, 0.25])[0]
                
                # Get cost from SOR
                from detection_service import SOR_RATES
                sor = SOR_RATES.get(defect_type, {}).get(severity, {"rate_per_sqm": 300, "desc": "Default"})
                area = random.uniform(0.3, 3.0)
                cost = sor["rate_per_sqm"] * area
                total_cost += cost
                
                defect = models.RoadDefect(
                    road_name=road["road_name"],
                    road_id=road["road_id"],
                    state=road["state"],
                    chainage=random.uniform(0, road["total_length_km"] * 1000),
                    latitude=round(lat, 7),
                    longitude=round(lon, 7),
                    defect_type=defect_type,
                    severity=severity,
                    confidence=random.uniform(0.65, 0.98),
                    estimated_area_sqm=round(area, 2),
                    repair_cost=round(cost, 2),
                    repair_description=sor.get("desc", ""),
                    sor_rate_per_sqm=sor["rate_per_sqm"],
                    is_defect=True,
                    survey_id=survey.id,
                    timestamp=datetime.utcnow() - timedelta(
                        days=random.randint(1, 90),
                        hours=random.randint(0, 23)
                    ),
                )
                db.add(defect)
            
            survey.total_defects = n_defects
            survey.total_repair_cost = round(total_cost, 2)
    
    db.commit()
    
    return {
        "message": "Demo data seeded successfully!",
        "roads_created": len(demo_roads),
        "note": "Call GET /api/dashboard/stats to see the populated dashboard"
    }
