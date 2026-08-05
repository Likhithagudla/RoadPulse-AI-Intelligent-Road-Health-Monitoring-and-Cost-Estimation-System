"""
============================================================
Road AI - Detection Service
============================================================
This module provides the detection service that:
1. Takes an image/video frame as input
2. Runs YOLOv8 inference
3. Returns detected defects with severity and cost estimation
4. Integrates with GPS data for map plotting

This is the bridge between the AI model and the FastAPI backend.
"""

import os
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# ===================== CONFIGURATION =====================

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEIGHTS_PATH = os.path.join(ROOT, "weights", "best.pt")
CONFIG_PATH = os.path.join(ROOT, "config.yaml")
EXPORT_PATH = os.path.join(ROOT, "exported_models", "road_defect_detector.onnx")

# Default confidence threshold
DEFAULT_CONF = 0.01 # Base threshold allowing everything, custom logic filters it later
DEFAULT_IOU = 0.45

# --- REFINED CLASS-SPECIFIC THRESHOLDS ---
# Lowered thresholds significantly to ensure model "responds" to all learned defects
CLASS_THRESHOLDS = {
    "pothole": 0.08,             # Lowered from 0.18
    "edge_deterioration": 0.08,  # Lowered from 0.18
    "alligator_cracking": 0.06,  # Lowered from 0.18 (Cracks are harder to see)
    "rutting": 0.08,             # Lowered from 0.18
    "subsidence": 0.08,          # Lowered from 0.18
    "cracking": 0.05,            # Lowered from 0.12
    "bleeding": 0.08,            # Lowered from 0.18
    "fretting": 0.05,            # Lowered from 0.12
    "ravelling": 0.05,           # Lowered from 0.12
    "repaired_pothole": 0.08,    # Lowered from 0.18
    "line_marking": 0.05,
    "storm_drain": 0.05,
    "manhole": 0.03,             # Highly sensitive
    "guard_rail": 0.05,
    "traffic_sign": 0.15,        # Lowered from 0.35
    "road_sign": 0.15,
}


# ===================== SOR RATES =====================

SOR_RATES = {
    "Pothole": {
        "Low":    {"rate_per_sqm": 350,  "desc": "Cold mix patching"},
        "Medium": {"rate_per_sqm": 550,  "desc": "Hot mix patching"},
        "High":   {"rate_per_sqm": 850,  "desc": "Deep repair with base course"},
    },
    "Edge_Deterioration": {
        "Low":    {"rate_per_sqm": 250,  "desc": "Edge seal coating"},
        "Medium": {"rate_per_sqm": 450,  "desc": "Edge patching"},
        "High":   {"rate_per_sqm": 750,  "desc": "Edge reconstruction"},
    },
    "Alligator_Cracking": {
        "Low":    {"rate_per_sqm": 200,  "desc": "Crack sealing"},
        "Medium": {"rate_per_sqm": 600,  "desc": "Overlay patching"},
        "High":   {"rate_per_sqm": 1200, "desc": "Full depth reclamation"},
    },
    "Rutting": {
        "Low":    {"rate_per_sqm": 300,  "desc": "Surface leveling"},
        "Medium": {"rate_per_sqm": 700,  "desc": "Milling and overlay"},
        "High":   {"rate_per_sqm": 1500, "desc": "Full reconstruction"},
    },
    "Subsidence": {
        "Low":    {"rate_per_sqm": 400,  "desc": "Surface patching"},
        "Medium": {"rate_per_sqm": 900,  "desc": "Sub-base repair"},
        "High":   {"rate_per_sqm": 2000, "desc": "Full reconstruction"},
    },
    "Cracking": {
        "Low":    {"rate_per_sqm": 150,  "desc": "Crack filling"},
        "Medium": {"rate_per_sqm": 400,  "desc": "Routing and sealing"},
        "High":   {"rate_per_sqm": 800,  "desc": "Full overlay"},
    },
    "Bleeding": {
        "Low":    {"rate_per_sqm": 100,  "desc": "Sand blotting"},
        "Medium": {"rate_per_sqm": 300,  "desc": "Micro-surfacing"},
        "High":   {"rate_per_sqm": 600,  "desc": "Resurfacing"},
    },
    "Fretting": {
        "Low":    {"rate_per_sqm": 200,  "desc": "Fog seal"},
        "Medium": {"rate_per_sqm": 450,  "desc": "Surface dressing"},
        "High":   {"rate_per_sqm": 800,  "desc": "Resurfacing"},
    },
    "Repaired_Pothole": {
        "Low":    {"rate_per_sqm": 100,  "desc": "Monitoring only"},
        "Medium": {"rate_per_sqm": 350,  "desc": "Re-patching"},
        "High":   {"rate_per_sqm": 650,  "desc": "Redo repair"},
    },
    "Manhole": {
        "Low":    {"rate_per_sqm": 50,    "desc": "Monitoring"},
        "Medium": {"rate_per_sqm": 500,   "desc": "Leveling/Grouting"},
        "High":   {"rate_per_sqm": 1500,  "desc": "Frame replacement"},
    },
}

# Generic fallback for any road damage
SOR_RATES["road_damage"] = {
    "Low":    {"rate_per_sqm": 200,  "desc": "Surface patching"},
    "Medium": {"rate_per_sqm": 500,  "desc": "Overlay repair"},
    "High":   {"rate_per_sqm": 1000, "desc": "Full reconstruction"},
}
SOR_RATES["pothole"] = SOR_RATES["Pothole"]
SOR_RATES["cracking"] = SOR_RATES["Cracking"]
SOR_RATES["manhole"] = SOR_RATES["Manhole"]

SEVERITY_THRESHOLDS = {
    "Pothole":              {"low": 0.005, "medium": 0.02},
    "pothole":              {"low": 0.005, "medium": 0.02},
    "Edge_Deterioration":   {"low": 0.01,  "medium": 0.05},
    "Alligator_Cracking":   {"low": 0.02,  "medium": 0.08},
    "Rutting":              {"low": 0.03,  "medium": 0.10},
    "Subsidence":           {"low": 0.01,  "medium": 0.04},
    "Cracking":             {"low": 0.01,  "medium": 0.05},
    "cracking":             {"low": 0.01,  "medium": 0.05},
    "Bleeding":             {"low": 0.02,  "medium": 0.08},
    "Fretting":             {"low": 0.02,  "medium": 0.06},
    "Repaired_Pothole":     {"low": 0.01,  "medium": 0.03},
    "Manhole":              {"low": 0.02,  "medium": 0.08},
    "manhole":              {"low": 0.02,  "medium": 0.08},
    "road_damage":          {"low": 0.01,  "medium": 0.05},
}


class RoadDefectDetector:
    """
    Main detection class that wraps the YOLOv8 model.
    Used by the FastAPI backend for inference.
    """
    
    def __init__(self, model_path: str = None, conf: float = DEFAULT_CONF, iou: float = DEFAULT_IOU):
        """
        Initialize the detector.
        
        Args:
            model_path: Path to the YOLOv8 weights (.pt or .onnx)
            conf: Confidence threshold
            iou: IoU threshold for NMS
        """
        self.models = []
        self.conf = conf
        self.iou = iou
        self.class_names = {}
        
        # Single Model path for Segmentation
        self.model_paths = [
            os.path.join(ROOT, "weights", "best.pt")
        ]
        
        self._load_config()
        self._load_models()
    
    def _load_config(self):
        """Load class names from config or from model itself."""
        # Default class names - will be overridden by model if available
        self.class_names = {}
        
        # Try loading from config file
        if os.path.exists(CONFIG_PATH):
            import yaml
            with open(CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f)
            names = config.get('names', {})
            if names:
                # Convert list format to dict if needed
                if isinstance(names, list):
                    self.class_names = {i: n for i, n in enumerate(names)}
                else:
                    self.class_names = names
    
    def _load_models(self):
        """Load multiple YOLOv8 models for ensemble."""
        try:
            import torch
            import torch.serialization
            
            # PyTorch 2.6+ defaults weights_only=True which breaks YOLO loading.
            # We must patch torch.load BEFORE ultralytics imports it.
            _original_torch_load = torch.load
            def _patched_torch_load(*args, **kwargs):
                kwargs['weights_only'] = False
                return _original_torch_load(*args, **kwargs)
            torch.load = _patched_torch_load
            
            try:
                from ultralytics.nn.tasks import SegmentationModel, DetectionModel
                torch.serialization.add_safe_globals([SegmentationModel, DetectionModel])
                print("[INFO] Added ultralytics models to safe globals")
            except Exception as e:
                print(f"[WARN] Failed to add safe globals: {e}")
            
            from ultralytics import YOLO
            
            # Also patch the reference inside ultralytics.nn.tasks module
            try:
                import ultralytics.nn.tasks as _tasks_mod
                _tasks_mod.torch.load = _patched_torch_load
            except Exception:
                pass
            
            for path in self.model_paths:
                if os.path.exists(path):
                    m = YOLO(path)
                    self.models.append(m)
                    # Sync class names from the first available model
                    if hasattr(m, 'names') and m.names:
                        self.class_names = m.names
                    print(f"[OK] Ensemble - Loaded: {path}")
                else:
                    print(f"[WARN] Ensemble - Missing: {path}")
            
            if not self.models:
                print("[WARN] No models found, using fallback segmentation model")
                self.models.append(YOLO('yolov8n-seg.pt'))
                self.class_names = self.models[0].names
            
            # Restore original torch.load
            torch.load = _original_torch_load
        except ImportError:
            print("[ERROR] ultralytics not installed.")
            self.models = []
    
    def _apply_nms(self, detections: List[Dict], iou_threshold: float) -> List[Dict]:
        """
        Applies Non-Maximum Suppression (NMS) to a list of detections.
        
        Args:
            detections: A list of detection dictionaries, each with 'bbox' and 'confidence'.
            iou_threshold: The IoU threshold for NMS.
            
        Returns:
            A list of filtered detections.
        """
        if not detections:
            return []

        # Extract bounding boxes, confidences, and class IDs
        boxes = []
        confidences = []
        class_ids = []
        for det in detections:
            bbox = det['bbox']
            boxes.append([bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']])
            confidences.append(det['confidence'])
            class_ids.append(det['class_id'])

        boxes = np.array(boxes)
        confidences = np.array(confidences)
        class_ids = np.array(class_ids)

        # Sort by confidence
        sorted_indices = np.argsort(confidences)[::-1]

        keep_indices = []
        while len(sorted_indices) > 0:
            # Pick the detection with the highest confidence
            best_idx = sorted_indices[0]
            keep_indices.append(best_idx)

            # Calculate IoU with all other remaining detections
            best_box = boxes[best_idx]
            remaining_indices = sorted_indices[1:]

            if len(remaining_indices) == 0:
                break

            remaining_boxes = boxes[remaining_indices]

            # Calculate intersection coordinates
            x1 = np.maximum(best_box[0], remaining_boxes[:, 0])
            y1 = np.maximum(best_box[1], remaining_boxes[:, 1])
            x2 = np.minimum(best_box[2], remaining_boxes[:, 2])
            y2 = np.minimum(best_box[3], remaining_boxes[:, 3])

            # Calculate intersection area
            intersection_area = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)

            # Calculate union area
            best_box_area = (best_box[2] - best_box[0]) * (best_box[3] - best_box[1])
            remaining_boxes_area = (remaining_boxes[:, 2] - remaining_boxes[:, 0]) * \
                                   (remaining_boxes[:, 3] - remaining_boxes[:, 1])
            union_area = best_box_area + remaining_boxes_area - intersection_area

            # Calculate IoU
            iou = intersection_area / (union_area + 1e-6) # Add epsilon to prevent division by zero

            # Filter out detections with high IoU (and same class)
            # Only suppress if IoU is high AND classes are the same
            # Or if IoU is very high regardless of class (e.g., 0.95)
            suppress_mask = (iou > iou_threshold) & (class_ids[remaining_indices] == class_ids[best_idx])
            # Add a condition for very high IoU regardless of class to catch near-identical boxes
            suppress_mask = suppress_mask | (iou > 0.95)

            sorted_indices = sorted_indices[1:][~suppress_mask]

        return [detections[i] for i in keep_indices]

    def detect_image(self, image_path: str, gps: Optional[Dict] = None, heading: Optional[float] = None) -> Dict:
        """
        Detect road defects in a single image.
        
        Args:
            image_path: Path to the image file
            gps: Optional GPS data {"latitude": float, "longitude": float}
        
        Returns:
            List of detection dictionaries
        """
        if not self.models:
            return []
        
        all_results = []
        for model in self.models:
            res = model.predict(
                source=image_path,
                conf=self.conf,
                iou=self.iou,
                imgsz=640,  # Increased from 416 for better detection of small cracks
                verbose=False,
            )
            all_results.extend(res)
        
        # Combined detections pass through merging logic
        detections = []
        raw_detections = []
        
        for r in all_results:
            img_h, img_w = r.orig_shape
            img_area = img_h * img_w
            
            has_masks = hasattr(r, 'masks') and r.masks is not None
            segments = r.masks.xy if has_masks else []
            
            for i, box in enumerate(r.boxes):
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                # Get class name
                cls_name = self.class_names.get(cls_id, f"Unknown_{cls_id}")
                
                # User preference renaming
                if cls_name.lower() == "fretting":
                    cls_name = "Ravelling"

                # APPLY BALANCED CLASS-SPECIFIC THRESHOLDS
                req_conf = CLASS_THRESHOLDS.get(cls_name.lower(), 0.05)
                if confidence < req_conf:
                    continue
                
                # Calculate area ratio for severity
                box_area = (x2 - x1) * (y2 - y1)
                area_ratio = box_area / img_area
                
                # Estimate real-world area (approximate)
                # Assuming camera at ~1.5m height, covering ~3m width at road level
                real_width_m = 3.0  # approximate road width visible
                pixels_per_meter = img_w / real_width_m
                real_area_sqm = box_area / (pixels_per_meter ** 2)
                
                # Classify severity
                severity = self._classify_severity(area_ratio, cls_name)
                
                # Estimate repair cost
                cost_info = self._estimate_cost(cls_name, severity, real_area_sqm)
                
                polygon = None
                if has_masks and i < len(segments):
                    poly = segments[i].tolist()
                    step = max(1, len(poly) // 40)  # Max 40 points per mask to compress JSON
                    polygon = [[round(px, 1), round(py, 1)] for px, py in poly[::step]]
                
                detection = {
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": round(confidence, 4),
                    "bbox": {
                        "x1": round(x1, 1),
                        "y1": round(y1, 1),
                        "x2": round(x2, 1),
                        "y2": round(y2, 1),
                    },
                    "polygon": polygon,
                    "area_ratio": round(area_ratio, 6),
                    "estimated_area_sqm": round(real_area_sqm, 3),
                    "severity": severity,
                    "repair_cost": cost_info,
                    "timestamp": datetime.now().isoformat(),
                }
                
                if gps:
                    if heading is not None:
                        dist_m = self._estimate_distance(y2, img_h)
                        defect_gps = self._apply_homography(gps, heading, dist_m)
                        detection["latitude"] = defect_gps["latitude"]
                        detection["longitude"] = defect_gps["longitude"]
                    else:
                        detection["latitude"] = gps.get("latitude")
                        detection["longitude"] = gps.get("longitude")
                
                detection["is_defect"] = True
                
                # Label non-defect items as N/A severity but keep them visible
                # In config: 9:Line_Marking, 10:Storm_Drain, 11:Manhole, 12:Guard_Rail, 13:Traffic_Sign
                infrastructure_ids = [9, 10, 11, 12, 13]
                if cls_id in infrastructure_ids:
                    # Manholes are treat as defects - don't set N/A
                    if cls_name.lower() != "manhole" and cls_name.lower() != "pothole":
                        detection["severity"] = "N/A"
                        detection["repair_cost"] = {"cost": 0, "desc": "Infrastructure item"}
                
                raw_detections.append(detection)
        
        # APPLY NMS TO MERGE DUPLICATES FROM DUAL MODELS
        detections = self._apply_nms(raw_detections, iou_threshold=0.45)
        
        # Get dimensions from last result if available
        last_h, last_w = (all_results[-1].orig_shape) if all_results else (480, 640)

        return {
            "total_detections": len(detections),
            "orig_width": last_w,
            "orig_height": last_h,
            "detections": detections
        }
    
    def detect_frame(self, frame: np.ndarray, gps: Optional[Dict] = None, heading: Optional[float] = None) -> List[Dict]:
        """
        Detect road defects in a video frame (numpy array).
        
        Args:
            frame: OpenCV frame (BGR numpy array)
            gps: Optional GPS data
        
        Returns:
            List of detection dictionaries
        """
        if not self.models:
            return []
        
        all_results = []
        for model in self.models:
            res = model.predict(
                source=frame,
                conf=self.conf,
                iou=self.iou,
                imgsz=640, # Increased from 416
                verbose=False,
            )
            all_results.extend(res)
        
        raw_detections = []
        for r in all_results:
            img_h, img_w = r.orig_shape
            img_area = img_h * img_w
            
            has_masks = hasattr(r, 'masks') and r.masks is not None
            segments = r.masks.xy if has_masks else []
            
            for i, box in enumerate(r.boxes):
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                cls_name = self.class_names.get(cls_id, f"Unknown_{cls_id}")
                
                if cls_name.lower() == "fretting":
                    cls_name = "Ravelling"
                
                # APPLY BALANCED CLASS-SPECIFIC THRESHOLDS
                req_conf = CLASS_THRESHOLDS.get(cls_name.lower(), 0.05)
                if confidence < req_conf:
                    continue
                
                box_area = (x2 - x1) * (y2 - y1)
                area_ratio = box_area / img_area
                
                real_width_m = 3.0
                pixels_per_meter = img_w / real_width_m
                real_area_sqm = box_area / (pixels_per_meter ** 2)
                
                severity = self._classify_severity(area_ratio, cls_name)
                cost_info = self._estimate_cost(cls_name, severity, real_area_sqm)
                
                polygon = None
                if has_masks and i < len(segments):
                    poly = segments[i].tolist()
                    step = max(1, len(poly) // 40)
                    polygon = [[round(px, 1), round(py, 1)] for px, py in poly[::step]]
                
                detection = {
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": round(confidence, 4),
                    "bbox": {
                        "x1": round(x1, 1), "y1": round(y1, 1),
                        "x2": round(x2, 1), "y2": round(y2, 1),
                    },
                    "polygon": polygon,
                    "severity": severity,
                    "estimated_area_sqm": round(real_area_sqm, 3),
                    "repair_cost": cost_info,
                    "is_defect": True,
                    "timestamp": datetime.now().isoformat(),
                }
                
                # Label non-defect items as N/A severity but keep them visible
                # In config: 9:Line_Marking, 10:Storm_Drain, 11:Manhole, 12:Guard_Rail, 13:Traffic_Sign
                infrastructure_ids = [9, 10, 11, 12, 13]
                if cls_id in infrastructure_ids:
                    # Manholes are treated as defects - don't set N/A
                    if cls_name.lower() != "manhole" and cls_name.lower() != "pothole":
                        detection["severity"] = "N/A"
                        detection["repair_cost"] = {"cost": 0, "desc": "Infrastructure item"}
                
                if gps:
                    if heading is not None:
                        dist_m = self._estimate_distance(y2, img_h)
                        defect_gps = self._apply_homography(gps, heading, dist_m)
                        detection["latitude"] = defect_gps["latitude"]
                        detection["longitude"] = defect_gps["longitude"]
                    else:
                        detection["latitude"] = gps.get("latitude")
                        detection["longitude"] = gps.get("longitude")
                
                raw_detections.append(detection)
        
        # APPLY NMS TO MERGE DUPLICATES
        detections = self._apply_nms(raw_detections, iou_threshold=0.45)
        return detections
    
    def process_video(self, video_path: str, gps_data: Optional[List[Dict]] = None,
                      frame_interval: int = 15) -> Dict:
        """
        Process a video file and detect defects at regular intervals.
        
        Args:
            video_path: Path to video file
            gps_data: Optional list of GPS points with timestamps
            frame_interval: Process every Nth frame
        
        Returns:
            Summary dict with all detections
        """
        import cv2
        
        if not gps_data:
            print("[INFO] No GPS data provided in video. Detections will not have geo-coordinates.")
            # No fallback to Maharashtra anymore - we want real data!
            gps_data = []
        else:
            print(f"[INFO] Processing video with {len(gps_data)} GPS points.")
            gps_data = self._smooth_gps_data(gps_data, window_size=7)
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"error": f"Cannot open video: {video_path}"}
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        all_detections = []
        frame_count = 0
        processed = 0
        
        print(f"Processing video: {video_path}")
        print(f"FPS: {fps}, Total frames: {total_frames}")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                # Get interpolated GPS and Heading if available
                gps = None
                heading = None
                if gps_data:
                    # GPS sensors often have a hardware latency of around 0.2s - 0.8s.
                    # We add a slight offset to 'look ahead' into the GPS buffer to find 
                    # where the car actually was when the light hit the camera sensor.
                    GPS_SYNC_OFFSET = 0.3 
                    
                    # Get exact car location at current frame
                    time_sec = (frame_count / fps) + GPS_SYNC_OFFSET
                    gps = self._interpolate_gps(gps_data, time_sec)
                    
                    # Use recorded heading if available (from phone/GPX), otherwise calculate from movement
                    if gps and gps.get('heading') is not None:
                        heading = gps['heading']
                    else:
                        # Calculate heading by looking 0.5s ahead from current interpolated time
                        future_gps = self._interpolate_gps(gps_data, time_sec + 0.5)
                        if gps and future_gps:
                            dist_moved = self._haversine(gps['latitude'], gps['longitude'], future_gps['latitude'], future_gps['longitude'])
                            # Only update heading if moved more than 0.2m to avoid noise/jitter
                            if dist_moved > 0.2:
                                heading = self._calculate_bearing(gps['latitude'], gps['longitude'], future_gps['latitude'], future_gps['longitude'])
                            else:
                                # Use last valid heading if stationary
                                heading = all_detections[-1].get('heading', 0.0) if all_detections else 0.0
                        else:
                            heading = 0.0 # Fallback
                
                detections = self.detect_frame(frame, gps, heading)
                
                # Check for defects and save frame + annotation
                if any(d.get("is_defect", False) for d in detections):
                    base_dir = os.path.dirname(video_path)
                    v_name = os.path.splitext(os.path.basename(video_path))[0]
                    frame_path = os.path.join(base_dir, f"{v_name}_frame_{frame_count}.jpg")
                    cv2.imwrite(frame_path, frame)
                    annot_path = self.get_annotated_image(frame_path)
                    
                    for d in detections:
                        d["temp_image_path"] = frame_path
                        d["temp_annot_path"] = annot_path

                for d in detections:
                    d['frame_number'] = frame_count
                    d['time_seconds'] = round(frame_count / fps, 2)
                
                all_detections.extend(detections)
                processed += 1
                
                if processed % 10 == 0:
                    print(f"  Processed {processed} frames ({frame_count}/{total_frames})...")
            
            frame_count += 1
        
        cap.release()
        
        # Deduplicate defects from consecutive frames using spatial clustering
        # Prevents logging the same pothole 5 times as the car drives past it
        all_detections = self._deduplicate_geo_clusters(all_detections, distance_threshold_m=7.0)
        
        # Build summary
        defect_summary = {}
        total_cost = 0
        
        for d in all_detections:
            if d.get('is_defect', False):
                cls = d['class_name']
                if cls not in defect_summary:
                    defect_summary[cls] = {"count": 0, "total_cost": 0, "severities": {}}
                defect_summary[cls]["count"] += 1
                cost = d.get('repair_cost', {}).get('cost', 0)
                defect_summary[cls]["total_cost"] += cost
                total_cost += cost
                
                sev = d['severity']
                if sev not in defect_summary[cls]["severities"]:
                    defect_summary[cls]["severities"][sev] = 0
                defect_summary[cls]["severities"][sev] += 1
        
        return {
            "video_path": video_path,
            "total_frames": total_frames,
            "frames_processed": processed,
            "fps": fps,
            "total_detections": len(all_detections),
            "total_defects": sum(1 for d in all_detections if d.get('is_defect')),
            "estimated_total_cost": round(total_cost, 2),
            "defect_summary": defect_summary,
            "detections": all_detections,
        }
    
    def _classify_severity(self, area_ratio: float, defect_type: str) -> str:
        """Classify defect severity based on area ratio."""
        thresholds = SEVERITY_THRESHOLDS.get(defect_type, {"low": 0.01, "medium": 0.05})
        
        if area_ratio < thresholds["low"]:
            return "Low"
        elif area_ratio < thresholds["medium"]:
            return "Medium"
        else:
            return "High"
    
    def _estimate_cost(self, defect_type: str, severity: str, area_sqm: float) -> Dict:
        """Estimate repair cost using SOR rates."""
        rates = SOR_RATES.get(defect_type, {}).get(severity, None)
        if rates is None:
            return {"cost": 0, "desc": "No SOR rate available"}
        
        cost = rates["rate_per_sqm"] * max(area_sqm, 0.5)  # Minimum 0.5 sqm
        return {
            "cost": round(cost, 2),
            "rate_per_sqm": rates["rate_per_sqm"],
            "area_sqm": round(area_sqm, 3),
            "desc": rates["desc"],
        }
    
    def _interpolate_gps(self, gps_data: List[Dict], time_sec: float) -> Dict:
        """Interpolate GPS coordinates for a given timestamp."""
        if not gps_data:
            return None
        
        # Find the two nearest GPS points
        for i in range(len(gps_data) - 1):
            t1 = gps_data[i].get('time', 0)
            t2 = gps_data[i + 1].get('time', 0)
            
            if t1 <= time_sec <= t2:
                ratio = (time_sec - t1) / (t2 - t1) if t2 != t1 else 0
                lat = gps_data[i]['latitude'] + ratio * (gps_data[i + 1]['latitude'] - gps_data[i]['latitude'])
                lon = gps_data[i]['longitude'] + ratio * (gps_data[i + 1]['longitude'] - gps_data[i]['longitude'])
                
                # Pass through heading from the nearest point
                heading = gps_data[i].get('heading')
                return {"latitude": round(lat, 7), "longitude": round(lon, 7), "heading": heading}
        
        # If outside range, return nearest
        if time_sec <= gps_data[0].get('time', 0):
            return {"latitude": gps_data[0]['latitude'], "longitude": gps_data[0]['longitude'], "heading": gps_data[0].get('heading')}
        return {"latitude": gps_data[-1]['latitude'], "longitude": gps_data[-1]['longitude'], "heading": gps_data[-1].get('heading')}
    
    def _smooth_gps_data(self, gps_data: List[Dict], window_size: int = 5) -> List[Dict]:
        """Applies a moving average filter to eliminate lateral GPS jitter."""
        if not gps_data or len(gps_data) < window_size:
            return gps_data
        
        smoothed = []
        hw = window_size // 2
        for i in range(len(gps_data)):
            start_idx = max(0, i - hw)
            end_idx = min(len(gps_data), i + hw + 1)
            
            subset = gps_data[start_idx:end_idx]
            
            avg_lat = sum(p['latitude'] for p in subset) / len(subset)
            avg_lon = sum(p['longitude'] for p in subset) / len(subset)
            
            # Weighted average with center having slightly more priority
            # For simplicity, simple moving average performs exceptionally well for vehicle trajectories
            
            smoothed_point = dict(gps_data[i])
            smoothed_point['latitude'] = avg_lat
            smoothed_point['longitude'] = avg_lon
            smoothed.append(smoothed_point)
            
        return smoothed
        
    def _estimate_distance(self, y2: float, img_h: float) -> float:
        """Estimate distance to defect based on bounding box y-coordinate using simplified IPM."""
        # Cap horizon at 40% down from top
        horizon = img_h * 0.4
        y2_clamped = max(y2, horizon + 1)
        
        # Ratio: approaches 0 at horizon, 1 at bottom
        ratio = (y2_clamped - horizon) / (img_h - horizon)
        ratio = max(0.01, min(1.0, ratio))
        
        # Simplified inverse mapping: 3m at bottom, ~300m at horizon (capped to 40m)
        dist = 3.0 / ratio
        return min(dist, 40.0)

    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate initial compass bearing from pt1 to pt2."""
        import math
        lat1, lat2 = math.radians(lat1), math.radians(lat2)
        diff_long = math.radians(lon2 - lon1)
        
        x = math.sin(diff_long) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(diff_long))
        
        return (math.degrees(math.atan2(x, y)) + 360) % 360

    def _apply_homography(self, base_gps: Dict, heading: float, distance_m: float) -> Dict:
        """Calculate destination GPS given base, heading, and distance."""
        import math
        R = 6371000 # Earth radius in m
        lat1, lon1 = math.radians(base_gps['latitude']), math.radians(base_gps['longitude'])
        brng = math.radians(heading)
        
        # Shift distance: In Road AI surveys, camera is typically seeing potholes 
        # around 3-15m in front of the car. We use the distance estimate to offset the point.
        lat2 = math.asin( math.sin(lat1)*math.cos(distance_m/R) + 
                          math.cos(lat1)*math.sin(distance_m/R)*math.cos(brng) )
        lon2 = lon1 + math.atan2(math.sin(brng)*math.sin(distance_m/R)*math.cos(lat1), 
                                 math.cos(distance_m/R)-math.sin(lat1)*math.sin(lat2))
        
        return {"latitude": round(math.degrees(lat2), 7), "longitude": round(math.degrees(lon2), 7)}

    def _haversine(self, lat1, lon1, lat2, lon2):
        import math
        R = 6371000 # Radius of earth in meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _deduplicate_geo_clusters(self, detections: List[Dict], distance_threshold_m: float = 3.5) -> List[Dict]:
        """
        Merge detections of the same class that are physically close to each other.
        This prevents tracking the same physical defect across multiple video frames as separate defects.
        """
        unique_detections = []
        for det in detections:
            if not det.get('is_defect', False) or 'latitude' not in det or 'longitude' not in det:
                unique_detections.append(det)
                continue
                
            lat1 = det.get('latitude')
            lon1 = det.get('longitude')
            if lat1 is None or lon1 is None:
                unique_detections.append(det)
                continue
            
            merged = False
            for u in unique_detections:
                if 'latitude' not in u or 'longitude' not in u or u.get('class_name') != det.get('class_name'):
                    continue
                
                lat2 = u.get('latitude')
                lon2 = u.get('longitude')
                if lat2 is None or lon2 is None:
                    continue
                
                dist = self._haversine(lat1, lon1, lat2, lon2)
                
                if dist <= distance_threshold_m:
                    # Merge logic: Keep the detection with higher confidence
                    if det.get('confidence', 0) > u.get('confidence', 0):
                        u['confidence'] = det['confidence']
                        u['estimated_area_sqm'] = max(u.get('estimated_area_sqm', 0), det.get('estimated_area_sqm', 0))
                        u['temp_image_path'] = det.get('temp_image_path', u.get('temp_image_path'))
                        u['temp_annot_path'] = det.get('temp_annot_path', u.get('temp_annot_path'))
                        u['latitude'] = lat1
                        u['longitude'] = lon1
                        u['repair_cost'] = det.get('repair_cost', u.get('repair_cost'))
                        u['severity'] = det.get('severity', u.get('severity'))
                        u['frame_number'] = det.get('frame_number', u.get('frame_number'))
                        u['time_seconds'] = det.get('time_seconds', u.get('time_seconds'))
                    merged = True
                    break
            
            if not merged:
                unique_detections.append(det)
                
        return unique_detections
    
    def get_annotated_image(self, image_path: str) -> Optional[str]:
        """
        Get annotated image with bounding boxes drawn.
        Returns path to annotated image.
        """
        if not self.models:
            return None
        
        # Use first model for basic annotation
        results = self.models[0].predict(
            source=image_path,
            conf=self.conf,
            iou=self.iou,
            imgsz=416,
            verbose=False,
        )
        
        for r in results:
            import cv2
            import numpy as np
            
            # Get original image
            annotated = r.orig_img.copy()
            
            # Map of class names to colors (BGR)
            color_map = {
                "pothole": (0, 0, 255),
                "minor-pothole": (144, 238, 144),
                "repaired_pothole": (0, 255, 0),
                "cracking": (0, 165, 255),
                "alligator_cracking": (0, 165, 255),
                "ravelling": (255, 100, 100),
                "fretting": (255, 100, 100),
                "trees": (144, 200, 144),
                "rutting": (255, 0, 0),
                "bleeding": (0, 255, 255),
                "edge_deterioration": (200, 150, 0),
                "storm_drain": (200, 200, 200),
                "manhole": (100, 100, 100)
            }
            
            masks = getattr(r, 'masks', None)
            boxes = getattr(r, 'boxes', None)
            
            if masks is not None and boxes is not None:
                # Create an overlay for all polygons
                overlay = annotated.copy()
                
                # Draw the polygons on the overlay
                for i, (box, mask_xy) in enumerate(zip(boxes, masks.xy)):
                    cls_id = int(box.cls[0])
                    cls_name = self.class_names.get(cls_id, f"Unknown_{cls_id}").lower()
                    
                    if cls_name == "fretting":
                        cls_name = "ravelling"
                        
                    color = color_map.get(cls_name, (255, 140, 0)) # Default orange
                    
                    pts = np.array(mask_xy, np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    cv2.fillPoly(overlay, [pts], color)
                
                # Blend overlay with original image
                cv2.addWeighted(overlay, 0.4, annotated, 0.6, 0, annotated)
                
                # Draw the labels
                for i, box in enumerate(boxes):
                    cls_id = int(box.cls[0])
                    cls_name = self.class_names.get(cls_id, f"Unknown_{cls_id}").lower()
                    if cls_name == "fretting":
                        cls_name = "ravelling"
                        
                    display_name = cls_name.replace("_", "-").upper()
                    
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 1.2
                    thickness = 2
                    
                    (text_w, text_h), baseline = cv2.getTextSize(display_name, font, font_scale, thickness)
                    
                    # Background rectangle
                    rect_y1 = int(y1) - text_h - 10
                    rect_y2 = int(y1)
                    if rect_y1 < 0:
                        rect_y1 = int(y1) + 10
                        rect_y2 = rect_y1 + text_h + 10
                    
                    cv2.rectangle(annotated, (int(x1), rect_y1), (int(x1) + text_w + 10, rect_y2), (0, 0, 0), -1)
                    cv2.putText(annotated, display_name, (int(x1) + 5, rect_y2 - 5), font, font_scale, (255, 255, 255), thickness)
            elif boxes is not None:
                 # Fallback if no segmentation masks exist
                 for box in boxes:
                    cls_id = int(box.cls[0])
                    cls_name = self.class_names.get(cls_id, f"Unknown").lower()
                    display_name = cls_name.replace("_", "-").upper()
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    (text_w, text_h), baseline = cv2.getTextSize(display_name, font, 1.2, 2)
                    cv2.rectangle(annotated, (int(x1), int(y1) - text_h - 10), (int(x1) + text_w + 10, int(y1)), (0, 0, 0), -1)
                    cv2.putText(annotated, display_name, (int(x1) + 5, int(y1) - 5), font, 1.2, (255, 255, 255), 2)
                    
            out_path = image_path.replace('.', '_annotated.')
            cv2.imwrite(out_path, annotated)
            return out_path
        
        return None


# ===================== SINGLETON INSTANCE =====================

_detector_instance = None

def get_detector() -> RoadDefectDetector:
    """Get or create the singleton detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = RoadDefectDetector()
    return _detector_instance


# ===================== CLI TEST =====================

if __name__ == "__main__":
    import sys
    
    detector = RoadDefectDetector()
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"\nDetecting defects in: {image_path}")
        detections = detector.detect_image(image_path)
        
        print(f"\nFound {len(detections)} detections:")
        for d in detections:
            print(f"  {d['class_name']} ({d['confidence']:.2f}) "
                  f"Severity: {d['severity']} "
                  f"Cost: ₹{d['repair_cost'].get('cost', 0):.0f}")
    else:
        print("Usage: python detection_service.py <image_path>")
        print("Or import: from detection_service import get_detector")
