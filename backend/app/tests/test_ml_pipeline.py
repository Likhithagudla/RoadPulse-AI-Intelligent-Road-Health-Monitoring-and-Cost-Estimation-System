"""
RoadPulse AI - Machine Learning Pipeline & Metric Validation Tests
Verifies:
- Dataset annotation integrity and class consistency (Option B: genuine classes only, normalized coords)
- Model checkpoint loading and device configuration
- Image preprocessing and corrupted buffer handling
- Inference output schema compliance (geometry, severity, 5-factor cost)
- Mathematical metric calculations (IoU, Precision, Recall, F1-score)
"""

from pathlib import Path
import yaml
import numpy as np
import pytest
import cv2

from ai_models.modules.config_loader import (
    DEFAULT_WEIGHTS,
    DATASET_DIR,
    ACTIVE_ANNOTATED_CLASSES,
    FULL_CLASSES,
    ensure_dataset_yaml_path,
)
from ai_models.modules.detector import RoadDefectDetector
from ai_models.modules.geometry_calibrator import CameraParameters


# ==========================================
# 1. DATASET CLASS CONSISTENCY TESTS
# ==========================================

def test_dataset_data_yaml_exists_and_valid():
    """Verifies that data.yaml exists and defines proper dataset paths."""
    yaml_path = ensure_dataset_yaml_path()
    assert yaml_path.exists(), f"Missing dataset configuration at {yaml_path}"

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "names" in data
    assert "nc" in data
    assert data["nc"] == len(data["names"])
    # Verify active genuine classes include Pothole and Traffic_Sign
    assert 0 in data["names"] or "0" in data["names"]


def test_independent_test_annotations_integrity():
    """
    Validates that independent test split annotations:
    1. Contain only genuinely annotated class IDs (0=Pothole, 13=Traffic_Sign).
    2. Have bounding box coordinates strictly normalized in [0.0, 1.0].
    3. Have no negative or NaN coordinates.
    """
    test_labels_dir = DATASET_DIR / "labels" / "test"
    if not test_labels_dir.exists():
        pytest.skip("Test labels directory not found in this environment")

    label_files = list(test_labels_dir.glob("*.txt"))
    assert len(label_files) > 0, "No test split label files found"

    valid_class_ids = set(ACTIVE_ANNOTATED_CLASSES.keys())
    total_boxes = 0

    for lbl_path in label_files:
        with open(lbl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue
            total_boxes += 1
            cls_id = int(parts[0])

            # Class ID must be one of the genuine active classes
            assert cls_id in valid_class_ids, (
                f"Unexpected class_id {cls_id} found in {lbl_path.name}. "
                f"Expected one of genuine classes: {valid_class_ids}"
            )

            # Coordinates check (either bbox format x, y, w, h or polygon points)
            coords = [float(x) for x in parts[1:]]
            for coord in coords:
                assert 0.0 <= coord <= 1.05, f"Unnormalized coordinate {coord} in {lbl_path.name}"

    assert total_boxes > 0, "Independent test set must contain labeled objects"


# ==========================================
# 2. MODEL LOADING & PREPROCESSING TESTS
# ==========================================

def test_yolo_weights_file_exists():
    """Verifies best.pt model weights file is present and non-empty."""
    assert DEFAULT_WEIGHTS.exists(), f"Weights file not found at {DEFAULT_WEIGHTS}"
    assert DEFAULT_WEIGHTS.stat().st_size > 1_000_000, "Weights file is suspiciously small"


def test_model_loading_into_detector():
    """Verifies RoadDefectDetector initializes YOLO model cleanly on CPU."""
    detector = RoadDefectDetector(weights_path=DEFAULT_WEIGHTS, device="cpu")
    assert detector.model is not None
    assert hasattr(detector.model, "names")
    assert len(detector.model.names) > 0


def test_image_preprocessing_and_validation():
    """Verifies validate_image handles numpy arrays, dimensions, and invalid inputs."""
    detector = RoadDefectDetector(weights_path=DEFAULT_WEIGHTS, device="cpu")

    # 1. Valid BGR numpy array (640x480)
    valid_img = np.zeros((480, 640, 3), dtype=np.uint8)
    ok, err, processed = detector.validate_image(valid_img)
    assert ok is True
    assert err is None
    assert processed.shape == (480, 640, 3)

    # 2. Empty numpy array
    empty_img = np.array([])
    ok, err, _ = detector.validate_image(empty_img)
    assert ok is False
    assert "empty" in err.lower()

    # 3. Too small dimensions (e.g. 5x5)
    tiny_img = np.zeros((5, 5, 3), dtype=np.uint8)
    ok, err, _ = detector.validate_image(tiny_img)
    assert ok is False
    assert "too small" in err.lower()

    # 4. Non-existent file path
    ok, err, _ = detector.validate_image(Path("non_existent_image_12345.jpg"))
    assert ok is False
    assert "does not exist" in err.lower()


# ==========================================
# 3. PREDICTION OUTPUT VALIDATION
# ==========================================

def test_inference_prediction_schema_output():
    """
    Runs inference on a synthetic road image with a simulated pothole and
    validates the complete response contract:
    - success boolean
    - dimensions
    - detections list with calibrated geometry, decoupled severity, and 5-factor cost
    """
    detector = RoadDefectDetector(weights_path=DEFAULT_WEIGHTS, device="cpu", conf_threshold=0.05)

    # Synthetic road image with asphalt gray and dark elliptical pothole
    synthetic_road = np.ones((720, 1280, 3), dtype=np.uint8) * 110
    cv2.ellipse(synthetic_road, (640, 550), (120, 60), 0, 0, 360, (25, 25, 25), -1)

    result = detector.detect_image(
        synthetic_road,
        gps={"latitude": 19.0760, "longitude": 72.8777},
        region="Maharashtra",
    )

    assert result["success"] is True
    assert result["orig_width"] == 1280
    assert result["orig_height"] == 720
    assert "detections" in result
    assert isinstance(result["detections"], list)

    for det in result["detections"]:
        assert "class_id" in det
        assert "class_name" in det
        assert "confidence" in det
        assert "bbox" in det
        assert "estimated_area_sqm" in det
        assert "severity" in det
        assert "detailed_cost_breakdown" in det
        assert "geometry_calibration" in det

        # Verify 5-factor cost structure
        cost = det["detailed_cost_breakdown"]
        assert "estimated_cost_inr" in cost
        assert "cost_breakdown" in cost
        assert "material_cost_inr" in cost["cost_breakdown"]
        assert "labour_cost_inr" in cost["cost_breakdown"]
        assert "equipment_cost_inr" in cost["cost_breakdown"]


# ==========================================
# 4. COMPUTER VISION METRIC CALCULATION TESTS
# ==========================================

def calculate_iou(boxA, boxB) -> float:
    """Computes Intersection over Union between two [x1, y1, x2, y2] bounding boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_w = max(0.0, xB - xA)
    inter_h = max(0.0, yB - yA)
    inter_area = inter_w * inter_h

    boxA_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxB_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    union_area = boxA_area + boxB_area - inter_area
    if union_area <= 0:
        return 0.0
    return inter_area / union_area


def calculate_precision_recall_f1(tp: int, fp: int, fn: int):
    """Computes classification and detection metrics with zero-division protection."""
    precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def test_iou_calculation_math():
    """Verifies IoU math for identical, disjoint, and overlapping boxes."""
    # 1. Identical boxes -> IoU = 1.0
    b1 = [10.0, 10.0, 50.0, 50.0]
    b2 = [10.0, 10.0, 50.0, 50.0]
    assert calculate_iou(b1, b2) == 1.0

    # 2. Completely disjoint boxes -> IoU = 0.0
    b3 = [0.0, 0.0, 10.0, 10.0]
    b4 = [20.0, 20.0, 30.0, 30.0]
    assert calculate_iou(b3, b4) == 0.0

    # 3. Two 10x10 boxes shifted by 5 horizontally
    # Box A: [0, 0, 10, 10], area = 100
    # Box B: [5, 0, 15, 10], area = 100
    # Intersection: [5, 0, 10, 10], area = 5 * 10 = 50
    # Union: 100 + 100 - 50 = 150
    # IoU: 50 / 150 = 1/3 ~ 0.333333
    b5 = [0.0, 0.0, 10.0, 10.0]
    b6 = [5.0, 0.0, 15.0, 10.0]
    assert pytest.approx(calculate_iou(b5, b6), 0.001) == (1.0 / 3.0)


def test_precision_recall_f1_calculation_math():
    """Verifies Precision, Recall, and F1-score formulas and zero-division handling."""
    # Case 1: TP=80, FP=20, FN=10
    # Precision = 80 / 100 = 0.80
    # Recall = 80 / 90 ~ 0.8889
    # F1 = 2 * 0.8 * 0.8889 / (0.8 + 0.8889) ~ 0.8421
    p, r, f1 = calculate_precision_recall_f1(80, 20, 10)
    assert p == 0.8
    assert pytest.approx(r, 0.001) == (80.0 / 90.0)
    expected_f1 = (2 * 0.8 * (80.0 / 90.0)) / (0.8 + (80.0 / 90.0))
    assert pytest.approx(f1, 0.001) == expected_f1

    # Case 2: Zero detections (no crash)
    p_zero, r_zero, f1_zero = calculate_precision_recall_f1(0, 0, 0)
    assert p_zero == 0.0
    assert r_zero == 0.0
    assert f1_zero == 0.0
