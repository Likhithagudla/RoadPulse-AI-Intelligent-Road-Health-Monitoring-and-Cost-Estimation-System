"""
RoadPulse AI - Inference Engine
Production-grade detector supporting single-image and batch video inference,
input validation, corrupted image resilience, calibrated ground-plane geometry,
physical severity classification (IRC 82:2015), and 5-factor SOR cost estimation (CPWD/MoRTH).
"""

import os
import cv2
import threading
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple

from .config_loader import (
    DEFAULT_WEIGHTS,
    get_device,
    patch_torch_load,
    FULL_CLASSES,
)
from .geometry_calibrator import GeometryCalibrator, CameraParameters
from .severity_classifier import SeverityClassifier
from .cost_estimator import CostEstimator
from .visualizer import ResultVisualizer


class RoadDefectDetector:
    """
    Thread-safe YOLOv8 inference service for RoadPulse AI.
    Integrates perspective geometry, physical severity classification,
    and civil engineering repair cost estimation.
    """

    def __init__(
        self,
        weights_path: Optional[Path] = None,
        conf_threshold: float = 0.15,
        iou_threshold: float = 0.45,
        device: Optional[str] = None,
        camera_params: Optional[CameraParameters] = None,
    ):
        patch_torch_load()
        self.weights_path = Path(weights_path) if weights_path else DEFAULT_WEIGHTS
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = get_device(device)
        self.model = None
        self.class_names: Dict[int, str] = {}
        self._lock = threading.Lock()

        # Analytical Modules
        self.geometry_calibrator = GeometryCalibrator(camera_params)
        self.severity_classifier = SeverityClassifier()
        self.cost_estimator = CostEstimator()

        self._load_model()

    def _load_model(self) -> None:
        """Loads YOLOv8 instance segmentation model into memory."""
        from ultralytics import YOLO

        if not self.weights_path.exists():
            print(f"[WARN] Checkpoint not found at {self.weights_path}. Checking fallback...")
            fallback = Path(self.weights_path).parent.parent / "yolov8n-seg.pt"
            if fallback.exists():
                self.weights_path = fallback
            else:
                self.weights_path = Path("yolov8n-seg.pt")

        print(f"[INFO] Initializing RoadDefectDetector with: {self.weights_path} on {self.device}")
        self.model = YOLO(str(self.weights_path))
        self.class_names = self.model.names if hasattr(self.model, "names") else FULL_CLASSES

    def validate_image(self, image_input: Union[str, Path, np.ndarray]) -> Tuple[bool, Optional[str], Optional[np.ndarray]]:
        """
        Validates image existence, format, decodability, and non-empty dimensions.
        Returns: (is_valid, error_message, decoded_bgr_array)
        """
        if isinstance(image_input, (str, Path)):
            p = Path(image_input)
            if not p.exists():
                return False, f"File does not exist: {p}", None
            if p.stat().st_size == 0:
                return False, f"File is empty (0 bytes): {p}", None
            
            # Read with OpenCV
            img = cv2.imread(str(p))
            if img is None:
                return False, f"Image file is corrupted or unsupported format: {p.name}", None
        elif isinstance(image_input, np.ndarray):
            img = image_input
            if img.size == 0:
                return False, "Input image numpy array is empty", None
        else:
            return False, "Invalid image input type", None

        h, w = img.shape[:2]
        if h < 10 or w < 10:
            return False, f"Image dimensions too small ({w}x{h}). Minimum size is 10x10.", None
        if h > 12000 or w > 12000:
            return False, f"Image dimensions exceed maximum safe limit ({w}x{h}).", None

        return True, None, img

    def detect_image(
        self,
        image_input: Union[str, Path, np.ndarray],
        gps: Optional[Dict[str, float]] = None,
        conf_override: Optional[float] = None,
        region: str = "Default",
        annotate: bool = False,
        output_annotated_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Detects road defects and infrastructure objects in a single image.
        Applies ground-plane geometry calibration, decoupled physical severity,
        and 5-factor CPWD/MoRTH repair cost estimation.
        """
        valid, err, img = self.validate_image(image_input)
        if not valid or img is None:
            return {
                "success": False,
                "error": err,
                "total_detections": 0,
                "detections": [],
            }

        img_h, img_w = img.shape[:2]
        conf = conf_override if conf_override is not None else self.conf_threshold

        # Update geometry calibrator frame dimensions
        self.geometry_calibrator.update_resolution(img_w, img_h)

        with self._lock:
            results = self.model.predict(
                source=img,
                conf=conf,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False,
            )

        detections: List[Dict[str, Any]] = []
        r = results[0]
        has_masks = hasattr(r, "masks") and r.masks is not None
        segments = r.masks.xy if has_masks else []

        total_repair_cost = 0.0

        for i, box in enumerate(r.boxes):
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            cls_name = self.class_names.get(cls_id, f"Unknown_{cls_id}")
            bbox_dict = {
                "x1": round(x1, 1),
                "y1": round(y1, 1),
                "x2": round(x2, 1),
                "y2": round(y2, 1),
            }

            # 1. Extract polygon and compute calibrated ground-plane area
            polygon = None
            poly_raw = None
            if has_masks and i < len(segments):
                poly_raw = segments[i].tolist()
                step = max(1, len(poly_raw) // 32)
                polygon = [[round(px, 1), round(py, 1)] for px, py in poly_raw[::step]]

            # Area calculation using perspective ground-plane ray casting
            if poly_raw and len(poly_raw) >= 3:
                phys_area_m2, geom_meta = self.geometry_calibrator.calculate_polygon_area_m2(poly_raw)
            else:
                phys_area_m2, geom_meta = self.geometry_calibrator.calculate_bbox_area_m2(bbox_dict)

            # 2. Engineering Severity Assessment (IRC 82:2015 / ASTM D6433)
            # Decoupled from AI detection confidence
            sev_meta = self.severity_classifier.classify_defect(
                defect_type=cls_name,
                physical_area_m2=phys_area_m2,
                dimensions=geom_meta,
                bbox=bbox_dict,
                polygon=poly_raw,
                ai_confidence=confidence,
            )
            severity = sev_meta.get("severity", "Low")

            # 3. Cost Estimation using Configurable Regional SOR (CPWD / MoRTH)
            cost_meta = self.cost_estimator.estimate_repair_cost(
                defect_type=cls_name,
                severity=severity,
                estimated_area_m2=phys_area_m2,
                is_calibrated=geom_meta.get("is_calibrated", False),
                region=region,
                confidence=confidence,
            )

            cost_inr = cost_meta.get("estimated_cost_inr", 0.0)
            total_repair_cost += cost_inr

            # Compact backward-compatible repair_cost dictionary
            patch_area = cost_meta.get("effective_patch_area_sqm", 0.0)
            rate_per_sqm = round(cost_inr / max(0.01, patch_area), 2) if patch_area > 0 else 0.0
            repair_cost_compact = {
                "rate_per_sqm": rate_per_sqm,
                "cost": cost_inr,
                "desc": cost_meta.get("repair_treatment", "Routine maintenance"),
            }

            is_defect = cls_name.lower() != "traffic_sign"

            item: Dict[str, Any] = {
                "class_id": cls_id,
                "class_name": cls_name,
                "confidence": round(confidence, 4),
                "is_defect": is_defect,
                "severity": severity,
                "bbox": bbox_dict,
                "polygon": polygon,
                "estimated_area_sqm": phys_area_m2,
                "repair_cost": repair_cost_compact,
                "detailed_cost_breakdown": cost_meta,
                "geometry_calibration": geom_meta,
                "severity_details": sev_meta,
                "timestamp": datetime.now().isoformat(),
            }

            if gps:
                item["latitude"] = gps.get("latitude")
                item["longitude"] = gps.get("longitude")

            detections.append(item)

        annotated_path = None
        if annotate and output_annotated_path:
            annotated_path = str(ResultVisualizer.save_annotated(img, Path(output_annotated_path), detections))

        return {
            "success": True,
            "orig_width": img_w,
            "orig_height": img_h,
            "total_detections": len(detections),
            "estimated_total_cost": round(total_repair_cost, 2),
            "region_applied": region,
            "detections": detections,
            "annotated_image_path": annotated_path,
        }

    def detect_frame(
        self,
        frame: np.ndarray,
        gps: Optional[Dict[str, float]] = None,
        heading: Optional[float] = None,
        region: str = "Default",
    ) -> List[Dict[str, Any]]:
        """Detect road defects in a video frame (numpy array)."""
        res = self.detect_image(frame, gps=gps, region=region)
        return res.get("detections", [])

    def get_annotated_image(self, image_path: str) -> Optional[str]:
        """
        Draw annotations onto image and save to temporary file.
        Returns the path to the annotated image.
        """
        import tempfile
        import uuid

        valid, err, img = self.validate_image(image_path)
        if not valid or img is None:
            return None

        res = self.detect_image(img, annotate=False)
        detections = res.get("detections", [])
        
        temp_dir = Path(tempfile.gettempdir()) / "roadpulse_annotated"
        temp_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex[:8]}_annotated.jpg"
        target_path = temp_dir / filename

        ResultVisualizer.save_annotated(img, target_path, detections)
        return str(target_path) if target_path.exists() else None

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Computes distance in meters between two GPS coordinates."""
        import math
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _deduplicate_geo_clusters(self, detections: List[Dict[str, Any]], distance_threshold_m: float = 3.5) -> List[Dict[str, Any]]:
        """
        Merge detections of the same class that are physically close to each other.
        Prevents tracking the same defect across consecutive video frames as separate items.
        """
        unique_detections: List[Dict[str, Any]] = []
        for det in detections:
            if not det.get("is_defect", False) or "latitude" not in det or "longitude" not in det:
                unique_detections.append(det)
                continue

            lat1 = det.get("latitude")
            lon1 = det.get("longitude")
            if lat1 is None or lon1 is None:
                unique_detections.append(det)
                continue

            merged = False
            for u in unique_detections:
                if "latitude" not in u or "longitude" not in u or u.get("class_name") != det.get("class_name"):
                    continue

                lat2 = u.get("latitude")
                lon2 = u.get("longitude")
                if lat2 is None or lon2 is None:
                    continue

                dist = self._haversine(lat1, lon1, lat2, lon2)
                if dist <= distance_threshold_m:
                    if det.get("confidence", 0) > u.get("confidence", 0):
                        u["confidence"] = det["confidence"]
                        u["estimated_area_sqm"] = max(u.get("estimated_area_sqm", 0), det.get("estimated_area_sqm", 0))
                        u["repair_cost"] = det.get("repair_cost", u.get("repair_cost"))
                        u["detailed_cost_breakdown"] = det.get("detailed_cost_breakdown", u.get("detailed_cost_breakdown"))
                        u["geometry_calibration"] = det.get("geometry_calibration", u.get("geometry_calibration"))
                        u["severity_details"] = det.get("severity_details", u.get("severity_details"))
                        u["severity"] = det.get("severity", u.get("severity"))
                        u["frame_number"] = det.get("frame_number", u.get("frame_number"))
                        u["time_seconds"] = det.get("time_seconds", u.get("time_seconds"))
                    merged = True
                    break

            if not merged:
                unique_detections.append(det)

        return unique_detections

    def process_video(
        self,
        video_path: Union[str, Path],
        gps_data: Optional[List[Dict[str, Any]]] = None,
        frame_interval: int = 15,
        conf_override: Optional[float] = None,
        region: str = "Default",
    ) -> Dict[str, Any]:
        """
        Processes video frames at regular intervals, interpolates GPS track data,
        and aggregates defect counts and repair budgets.
        """
        video_p = Path(video_path)
        if not video_p.exists():
            raise FileNotFoundError(f"Video file not found: {video_p}")

        cap = cv2.VideoCapture(str(video_p))
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video file: {video_p}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frame_idx = 0
        frames_processed = 0
        all_detections: List[Dict[str, Any]] = []
        total_cost = 0.0
        defect_summary: Dict[str, int] = {}

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                time_sec = round(frame_idx / fps, 2)

                # Match GPS point by timestamp if provided
                gps_point = None
                if gps_data:
                    # Find closest point in time
                    gps_point = min(gps_data, key=lambda p: abs(p.get("time", 0) - time_sec), default=None)

                gps_dict = {"latitude": gps_point["latitude"], "longitude": gps_point["longitude"]} if gps_point else None

                frame_res = self.detect_image(frame, gps=gps_dict, conf_override=conf_override, region=region)
                if frame_res.get("success"):
                    for d in frame_res["detections"]:
                        d["frame_number"] = frame_idx
                        d["time_seconds"] = time_sec
                        all_detections.append(d)

                        cost = d.get("repair_cost", {}).get("cost", 0.0)
                        total_cost += cost

                        cname = d["class_name"]
                        defect_summary[cname] = defect_summary.get(cname, 0) + 1

                frames_processed += 1

            frame_idx += 1

        cap.release()

        # Deduplicate detections physically close in space
        deduped = self._deduplicate_geo_clusters(all_detections) if gps_data else all_detections
        total_cost = sum(d.get("repair_cost", {}).get("cost", 0.0) for d in deduped)

        defect_summary = {}
        for d in deduped:
            cname = d["class_name"]
            defect_summary[cname] = defect_summary.get(cname, 0) + 1

        return {
            "total_frames": total_frames,
            "frames_processed": frames_processed,
            "total_detections": len(deduped),
            "total_defects": sum(1 for d in deduped if d.get("is_defect")),
            "estimated_total_cost": round(total_cost, 2),
            "region_applied": region,
            "defect_summary": defect_summary,
            "detections": deduped,
        }


# ===================== THREAD-SAFE SINGLETON =====================

_detector_instance: Optional[RoadDefectDetector] = None
_instance_lock = threading.Lock()


def get_detector() -> RoadDefectDetector:
    """Returns thread-safe singleton instance of RoadDefectDetector."""
    global _detector_instance
    with _instance_lock:
        if _detector_instance is None:
            _detector_instance = RoadDefectDetector()
        return _detector_instance
