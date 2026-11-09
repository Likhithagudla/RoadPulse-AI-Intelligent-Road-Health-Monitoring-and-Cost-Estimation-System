"""
RoadPulse AI - Road Defects & AI Inference Router
Handles image and video defect detection, GIS mapping, and defect lifecycle records.
"""

import os
import sys
import shutil
import uuid
import asyncio
import aiofiles
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
)
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ...core.config import settings
from ...core.database import get_db
from ...core.dependencies import get_current_user, get_optional_current_user, require_worker_or_admin
from ...models.user import User
from ...models.defect import RoadDefect
from ...models.survey import Survey
from ...models.road import Road
from ...models.detection_result import DetectionResult
from ...models.gps_coordinate import GPSCoordinate
from ...schemas.defect import DefectResponse, DefectListResponse, StatusUpdate
from ...utils.pagination import pagination_params
from ...utils.gps_parser import parse_srt_gps, calculate_pci_score, pci_to_condition_label

# Connect to AI detector module
AI_ROOT = Path(settings.AI_MODELS_DIR)
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from modules.detector import get_detector

router = APIRouter(tags=["Defects & AI Inference"])


@router.post("/detect", summary="Upload image for defect detection")
async def detect_defects(
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    road_name: Optional[str] = Form(None),
    chainage: Optional[float] = Form(None),
    survey_id: Optional[int] = Form(None),
    vibration_level: float = Form(0.0),
    region: str = Form("Default"),
    save_results: bool = Form(True),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Detects road surface distress in an uploaded image.
    Applies calibrated ground-plane perspective geometry, decoupled physical severity (IRC 82:2015),
    and 5-factor CPWD/MoRTH repair cost estimation.
    """
    # 1. Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image file format '{ext}'. Allowed: .jpg, .jpeg, .png, .webp",
        )

    file_id = uuid.uuid4().hex[:12]
    filename = f"{file_id}{ext}"
    image_dir = settings.upload_path / "images"
    image_path = image_dir / filename

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty (0 bytes).")

    async with aiofiles.open(image_path, "wb") as f:
        await f.write(content)

    # 2. Run inference in worker thread without blocking async event loop
    detector = get_detector()
    gps_dict = {"latitude": latitude, "longitude": longitude} if (latitude and longitude) else None
    infer_res = await asyncio.to_thread(detector.detect_image, image_path, gps=gps_dict, region=region)

    if not infer_res.get("success"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Inference failed on input image: {infer_res.get('error')}",
        )

    detections = infer_res.get("detections", [])
    orig_w = infer_res.get("orig_width", 0)
    orig_h = infer_res.get("orig_height", 0)

    # 3. Generate annotated image overlay in thread pool
    annotated_dir = settings.upload_path / "annotated"
    annotated_filename = f"annotated_{filename}"
    annotated_path = annotated_dir / annotated_filename
    temp_annotated = await asyncio.to_thread(detector.get_annotated_image, str(image_path))
    if temp_annotated and os.path.exists(temp_annotated):
        shutil.move(temp_annotated, str(annotated_path))

    web_image_url = f"/uploads/images/{filename}"
    web_annotated_url = f"/uploads/annotated/{annotated_filename}" if annotated_path.exists() else None

    # Resolve road metadata if road_name provided
    road_id = None
    state = None
    if road_name:
        road_record = db.query(Road).filter(Road.road_name.ilike(road_name.strip())).first()
        if road_record:
            road_id = road_record.road_id
            state = road_record.state

    # 4. Persist to database if requested
    saved_records = []
    if save_results and detections:
        for d in detections:
            bbox = d.get("bbox", {})
            repair = d.get("repair_cost", {})
            cost_details = d.get("detailed_cost_breakdown")
            geom_calib = d.get("geometry_calibration")
            sev_details = d.get("severity_details")

            defect = RoadDefect(
                road_name=road_name,
                road_id=road_id,
                state=state,
                chainage=chainage,
                latitude=latitude,
                longitude=longitude,
                defect_type=d["class_name"],
                severity=d.get("severity", "Low"),
                confidence=d["confidence"],
                bbox_x1=bbox.get("x1"),
                bbox_y1=bbox.get("y1"),
                bbox_x2=bbox.get("x2"),
                bbox_y2=bbox.get("y2"),
                estimated_area_sqm=d.get("estimated_area_sqm"),
                repair_cost=repair.get("cost", 0.0),
                repair_description=repair.get("desc"),
                sor_rate_per_sqm=repair.get("rate_per_sqm"),
                detailed_cost_breakdown=cost_details,
                geometry_calibration=geom_calib,
                severity_details=sev_details,
                image_path=web_image_url,
                annotated_image_path=web_annotated_url,
                vibration_level=vibration_level,
                polygon=d.get("polygon"),
                status="reported",
                is_defect=d.get("is_defect", True),
                reported_by=current_user.id if current_user else None,
                survey_id=survey_id,
            )
            db.add(defect)
            db.flush()

            # Record normalized detection instance
            det_record = DetectionResult(
                defect_id=defect.id,
                survey_id=survey_id,
                class_id=d.get("class_id", 0),
                class_name=d.get("class_name", "Unknown"),
                confidence=float(d.get("confidence", 0.0)),
                bbox_x1=float(bbox.get("x1", 0.0)),
                bbox_y1=float(bbox.get("y1", 0.0)),
                bbox_x2=float(bbox.get("x2", 0.0)),
                bbox_y2=float(bbox.get("y2", 0.0)),
                area_sqm=d.get("estimated_area_sqm"),
                severity=d.get("severity", "Low"),
                is_defect=d.get("is_defect", True),
                geometry_metadata=geom_calib,
                cost_metadata=cost_details,
                raw_polygon=d.get("polygon"),
            )
            db.add(det_record)
            saved_records.append(defect)

        db.commit()

        # Update survey metrics if attached to a survey
        if survey_id:
            survey = db.query(Survey).filter(Survey.id == survey_id).first()
            if survey:
                all_survey_defects = db.query(RoadDefect).filter(RoadDefect.survey_id == survey_id).all()
                survey.total_defects = len(all_survey_defects)
                survey.total_repair_cost = sum(df.repair_cost for df in all_survey_defects)
                high_count = sum(1 for df in all_survey_defects if df.severity == "High")
                survey.pci_score = calculate_pci_score(survey.total_defects, survey.total_length_km, high_count)
                survey.road_condition = pci_to_condition_label(survey.pci_score)
                db.commit()

    return {
        "success": True,
        "image_url": web_image_url,
        "annotated_image_url": web_annotated_url,
        "orig_width": orig_w,
        "orig_height": orig_h,
        "total_detections": len(detections),
        "estimated_total_cost": infer_res.get("estimated_total_cost", 0.0),
        "region_applied": region,
        "detections": detections,
    }


@router.post("/detect/video", summary="Upload video for batch defect detection")
async def detect_video(
    file: UploadFile = File(...),
    srt_file: Optional[UploadFile] = File(None),
    road_name: Optional[str] = Form(None),
    road_id: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    survey_id: Optional[int] = Form(None),
    frame_interval: int = Form(15),
    conf_threshold: float = Form(0.15),
    region: str = Form("Default"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Processes video file, extracts periodic frames, correlates SRT GPS, and logs survey defects."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported video format.")

    file_id = uuid.uuid4().hex[:12]
    video_filename = f"{file_id}{ext}"
    video_path = settings.upload_path / "videos" / video_filename

    async with aiofiles.open(video_path, "wb") as f:
        await f.write(await file.read())

    # Parse SRT if present
    gps_data = None
    if srt_file:
        srt_content = (await srt_file.read()).decode("utf-8", errors="ignore")
        gps_data = parse_srt_gps(srt_content)

    detector = get_detector()
    video_res = await asyncio.to_thread(
        detector.process_video,
        video_path=video_path,
        gps_data=gps_data,
        frame_interval=frame_interval,
        conf_override=conf_threshold,
        region=region,
    )

    # Save survey or update existing
    if not survey_id and road_name:
        survey = Survey(
            road_name=road_name,
            road_id=road_id,
            state=state,
            surveyor_name=current_user.username if current_user else "Video Upload",
            video_path=f"/uploads/videos/{video_filename}",
            total_defects=video_res["total_defects"],
            total_repair_cost=video_res["estimated_total_cost"],
            status="completed",
        )
        db.add(survey)
        db.commit()
        db.refresh(survey)
        survey_id = survey.id

    # Persist GPS track coordinates if present
    if gps_data and survey_id:
        for pt in gps_data:
            coord = GPSCoordinate(
                survey_id=survey_id,
                latitude=float(pt.get("latitude", 0.0)),
                longitude=float(pt.get("longitude", 0.0)),
                speed_kmh=pt.get("speed_kmh"),
                timestamp=datetime.now(timezone.utc),
            )
            db.add(coord)
        db.commit()

    # Persist defects
    if survey_id:
        for d in video_res.get("detections", []):
            bbox = d.get("bbox", {})
            repair = d.get("repair_cost", {})
            defect = RoadDefect(
                road_name=road_name,
                road_id=road_id,
                state=state,
                latitude=d.get("latitude"),
                longitude=d.get("longitude"),
                defect_type=d["class_name"],
                severity=d.get("severity", "Low"),
                confidence=d["confidence"],
                bbox_x1=bbox.get("x1"),
                bbox_y1=bbox.get("y1"),
                bbox_x2=bbox.get("x2"),
                bbox_y2=bbox.get("y2"),
                estimated_area_sqm=d.get("estimated_area_sqm"),
                repair_cost=repair.get("cost", 0.0),
                repair_description=repair.get("desc"),
                sor_rate_per_sqm=repair.get("rate_per_sqm"),
                detailed_cost_breakdown=d.get("detailed_cost_breakdown"),
                geometry_calibration=d.get("geometry_calibration"),
                severity_details=d.get("severity_details"),
                video_path=f"/uploads/videos/{video_filename}",
                frame_number=d.get("frame_number"),
                time_seconds=d.get("time_seconds"),
                polygon=d.get("polygon"),
                status="reported",
                is_defect=d.get("is_defect", True),
                reported_by=current_user.id if current_user else None,
                survey_id=survey_id,
            )
            db.add(defect)
        db.commit()

    return {
        "success": True,
        "video_url": f"/uploads/videos/{video_filename}",
        "survey_id": survey_id,
        "summary": video_res,
    }


@router.get("/defects", response_model=DefectListResponse, summary="List road defects with pagination")
def list_defects(
    road_name: Optional[str] = Query(None),
    defect_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_defect: Optional[bool] = Query(None),
    is_resolved: Optional[bool] = Query(None),
    survey_id: Optional[int] = Query(None),
    pagination: tuple = Depends(pagination_params),
    db: Session = Depends(get_db),
):
    """Returns filtered, paginated road distress records."""
    limit, offset = pagination
    query = db.query(RoadDefect)

    if road_name:
        query = query.filter(RoadDefect.road_name.ilike(f"%{road_name.strip()}%"))
    if defect_type:
        query = query.filter(RoadDefect.defect_type == defect_type.strip())
    if severity:
        query = query.filter(RoadDefect.severity == severity.strip())
    if status:
        query = query.filter(RoadDefect.status == status.strip())
    if is_defect is not None:
        query = query.filter(RoadDefect.is_defect == is_defect)
    if is_resolved is not None:
        query = query.filter(RoadDefect.is_resolved == is_resolved)
    if survey_id is not None:
        query = query.filter(RoadDefect.survey_id == survey_id)

    total = query.count()
    items = query.order_by(desc(RoadDefect.timestamp)).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "defects": items,
    }


@router.get("/defects/map", summary="Get GIS map coordinate points")
def get_defects_map(
    road_name: Optional[str] = Query(None),
    defect_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    survey_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Optimized lightweight endpoint for Leaflet/Mapbox GIS dashboard layers."""
    query = db.query(RoadDefect).filter(
        RoadDefect.latitude.isnot(None),
        RoadDefect.longitude.isnot(None),
        RoadDefect.is_defect == True,
    )

    if road_name:
        query = query.filter(RoadDefect.road_name.ilike(f"%{road_name.strip()}%"))
    if defect_type:
        query = query.filter(RoadDefect.defect_type == defect_type.strip())
    if severity:
        query = query.filter(RoadDefect.severity == severity.strip())
    if survey_id:
        query = query.filter(RoadDefect.survey_id == survey_id)

    defects = query.all()
    points = []
    for d in defects:
        points.append({
            "id": d.id,
            "latitude": d.latitude,
            "longitude": d.longitude,
            "defect_type": d.defect_type,
            "severity": d.severity,
            "confidence": d.confidence,
            "repair_cost": d.repair_cost,
            "road_name": d.road_name,
            "status": d.status,
            "image_path": d.image_path,
            "annotated_image_path": d.annotated_image_path,
        })

    return {"total": len(points), "points": points}


@router.get("/defects/{defect_id}", response_model=DefectResponse, summary="Get single defect by ID")
def get_defect(
    defect_id: int,
    db: Session = Depends(get_db),
):
    defect = db.query(RoadDefect).filter(RoadDefect.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Defect with ID {defect_id} not found.")
    return defect


@router.patch("/defects/{defect_id}/status", response_model=DefectResponse, summary="Update defect resolution status")
def update_defect_status(
    defect_id: int,
    status_update: StatusUpdate,
    current_user: User = Depends(require_worker_or_admin),
    db: Session = Depends(get_db),
):
    defect = db.query(RoadDefect).filter(RoadDefect.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Defect with ID {defect_id} not found.")

    defect.status = status_update.status
    if status_update.status in ("resolved", "completed"):
        defect.is_resolved = True
        defect.resolved_at = datetime.now(timezone.utc)
    elif status_update.status in ("reported", "assigned", "in_progress"):
        defect.is_resolved = False

    db.commit()
    db.refresh(defect)
    return defect


# ===================== CITIZEN / MOBILE REPORTING =====================

@router.post("/report", summary="Citizen defect submission")
async def report_issue(
    file: Optional[UploadFile] = File(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    road_name: Optional[str] = Form(None),
    defect_type: Optional[str] = Form("Pothole"),
    description: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Enables citizens and field workers to submit manual defect reports."""
    image_url = None
    annotated_url = None
    severity = "Medium"
    cost = 550.0

    if file:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            filename = f"report_{uuid.uuid4().hex[:10]}{ext}"
            save_path = settings.upload_path / "images" / filename
            with open(save_path, "wb") as f:
                f.write(await file.read())
            image_url = f"/uploads/images/{filename}"

            # Auto-run AI detection if photo provided
            try:
                det = get_detector()
                r = det.detect_image(save_path)
                if r.get("success") and r.get("detections"):
                    top = r["detections"][0]
                    defect_type = top["class_name"]
                    severity = top.get("severity", severity)
                    cost = top.get("repair_cost", {}).get("cost", cost)
            except Exception:
                pass

    new_defect = RoadDefect(
        road_name=road_name or "Reported Location",
        latitude=latitude,
        longitude=longitude,
        defect_type=defect_type or "Pothole",
        severity=severity,
        confidence=1.0,
        repair_cost=cost,
        repair_description=description or "Citizen reported distress",
        image_path=image_url,
        status="reported",
        is_defect=True,
        reported_by=current_user.id if current_user else None,
    )
    db.add(new_defect)
    db.commit()
    db.refresh(new_defect)

    return {"success": True, "message": "Issue reported successfully", "defect_id": new_defect.id}


@router.get("/issues/map", summary="Public map of reported issues")
def get_public_issues_map(db: Session = Depends(get_db)):
    """Returns reported road issues for the public map view."""
    return get_defects_map(db=db)
