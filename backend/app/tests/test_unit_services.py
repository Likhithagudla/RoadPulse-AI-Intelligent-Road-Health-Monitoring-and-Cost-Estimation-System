"""
RoadPulse AI - Comprehensive Unit Tests
Tests core services in isolation:
- Authentication, password hashing, password complexity, and JWT token management
- Geometry calibration (perspective projection, ray-plane intersection, polygon shoelace formula)
- Decoupled physical severity classification (IRC 82:2015, ASTM D6433)
- 5-factor civil engineering repair cost estimation (CPWD DSR, MoRTH, regional multipliers)
- Database model constraints and relationship integrity
- Pydantic schema validation
"""

import math
import pytest
from datetime import timedelta
import numpy as np
from pydantic import ValidationError

from app.core.security import SecurityService
from app.models.user import User
from app.models.defect import RoadDefect
from app.models.detection_result import DetectionResult
from app.models.survey import Survey
from app.models.gps_coordinate import GPSCoordinate
from app.schemas.user import UserRegister, UserCreateAdmin
from app.schemas.road import RoadCreate
from app.schemas.survey import SurveyCreate

from ai_models.modules.geometry_calibrator import CameraParameters, GeometryCalibrator
from ai_models.modules.severity_classifier import SeverityClassifier
from ai_models.modules.cost_estimator import CostEstimator


# ==========================================
# 1. AUTHENTICATION & SECURITY SERVICE TESTS
# ==========================================

def test_password_hashing_and_verification():
    """Verifies bcrypt hashing generates unique salts and verifies correctly."""
    plain = "SuperSecurePass123!"
    hash1 = SecurityService.get_password_hash(plain)
    hash2 = SecurityService.get_password_hash(plain)

    # Hashes must be different due to random salting
    assert hash1 != hash2
    assert SecurityService.verify_password(plain, hash1) is True
    assert SecurityService.verify_password(plain, hash2) is True
    assert SecurityService.verify_password("WrongPass123!", hash1) is False
    assert SecurityService.verify_password("", hash1) is False
    assert SecurityService.verify_password(plain, "") is False


def test_password_complexity_rules():
    """Verifies enterprise password complexity enforcement."""
    # Too short (<8)
    valid, msg = SecurityService.validate_password_strength("Short1!")
    assert valid is False
    assert "at least 8 characters" in msg.lower()

    # Missing uppercase
    valid, msg = SecurityService.validate_password_strength("lowercase123!")
    assert valid is False
    assert "uppercase" in msg.lower()

    # Missing lowercase
    valid, msg = SecurityService.validate_password_strength("UPPERCASE123!")
    assert valid is False
    assert "lowercase" in msg.lower()

    # Missing digit
    valid, msg = SecurityService.validate_password_strength("NoDigitsHere!")
    assert valid is False
    assert "digit" in msg.lower()

    # Fully compliant
    valid, msg = SecurityService.validate_password_strength("ValidP@ssw0rd2026")
    assert valid is True
    assert msg is None


def test_jwt_token_creation_and_claims():
    """Verifies JWT access token payload structure and expiration."""
    data = {"sub": "engineer_alice", "role": "worker"}
    token = SecurityService.create_access_token(data=data, expires_delta=timedelta(minutes=30))
    decoded = SecurityService.decode_token(token)

    assert decoded["sub"] == "engineer_alice"
    assert decoded["role"] == "worker"
    assert decoded["type"] == "access"
    assert "exp" in decoded
    assert "iat" in decoded


# ==========================================
# 2. GEOMETRY CALIBRATION TESTS
# ==========================================

def test_camera_parameters_initialization():
    """Verifies optical parameter and horizon row computation."""
    params = CameraParameters(
        mount_height_m=1.4,
        pitch_deg=14.0,
        fov_v_deg=55.0,
        fov_h_deg=70.0,
        image_width=1920,
        image_height=1080,
    )
    assert params.cx == 960.0
    assert params.cy == 540.0
    assert params.fy > 0
    assert params.fx > 0
    # Horizon row must be above optical center cy for downward tilted camera
    assert params.horizon_y < params.cy


def test_pixel_to_ground_perspective_projection():
    """Verifies ray-plane projection from image pixels to road plane."""
    calibrator = GeometryCalibrator()
    calibrator.update_resolution(1920, 1080)

    # Point near bottom of image (close to vehicle bumper)
    x_close, z_close, ok_close = calibrator.pixel_to_ground(960.0, 950.0)
    assert ok_close is True
    assert z_close is not None and z_close > 0.5
    # Point at center column should have ~0 lateral offset
    assert abs(x_close) < 0.2

    # Point near horizon (far away)
    x_far, z_far, ok_far = calibrator.pixel_to_ground(960.0, 500.0)
    assert ok_far is True
    assert z_far > z_close  # Further down road

    # Point above horizon (sky / background) must be rejected
    x_sky, z_sky, ok_sky = calibrator.pixel_to_ground(960.0, 200.0)
    assert ok_sky is False
    assert x_sky is None
    assert z_sky is None


def test_polygon_area_shoelace_calculation():
    """Verifies shoelace formula area calculation on calibrated ground polygon."""
    calibrator = GeometryCalibrator()
    calibrator.update_resolution(1920, 1080)

    # Define a rectangular patch in image coordinates located safely on road surface
    patch = [
        [900.0, 800.0],
        [1020.0, 800.0],
        [1020.0, 900.0],
        [900.0, 900.0],
    ]
    area, meta = calibrator.calculate_polygon_area_m2(patch)
    assert area > 0.0
    assert meta["is_calibrated"] is True
    assert "method" in meta

    # Insufficient vertices (<3)
    bad_patch = [[100.0, 100.0], [200.0, 200.0]]
    bad_area, bad_meta = calibrator.calculate_polygon_area_m2(bad_patch)
    assert bad_area == 0.0
    assert bad_meta["is_calibrated"] is False


# ==========================================
# 3. SEVERITY CLASSIFICATION TESTS (IRC 82)
# ==========================================

def test_pothole_severity_thresholds_irc82():
    """Verifies defect physical severity thresholds based on physical area and defect hazard weights."""
    # Minor surface defect (Low severity)
    sev_low = SeverityClassifier.classify_defect(
        defect_type="Bleeding",
        physical_area_m2=0.02,
        ai_confidence=0.99,  # High confidence must NOT inflate minor defect to High severity!
    )
    assert sev_low["severity"] == "Low"
    assert "Minor" in sev_low["hazard_level"]

    # Moderate defect (0.10 m^2 Edge Deterioration -> Medium severity)
    sev_med = SeverityClassifier.classify_defect(
        defect_type="Edge_Deterioration",
        physical_area_m2=0.10,
        ai_confidence=0.50,
    )
    assert sev_med["severity"] == "Medium"

    # Severe pothole (> 0.6 m^2)
    sev_high = SeverityClassifier.classify_defect(
        defect_type="Pothole",
        physical_area_m2=0.85,
        ai_confidence=0.30,  # Low confidence must NOT diminish severe physical damage!
    )
    assert sev_high["severity"] == "High"
    assert "Critical" in sev_high["hazard_level"]


def test_infrastructure_asset_non_distress():
    """Verifies non-distress infrastructure elements are classified as N/A."""
    res = SeverityClassifier.classify_defect(
        defect_type="Traffic_Sign",
        physical_area_m2=1.5,
    )
    assert res["severity"] == "N/A"
    assert res["hazard_level"] == "Non-Distress"


# ==========================================
# 4. COST ESTIMATION SERVICE TESTS
# ==========================================

def test_cost_estimator_mathematical_identity():
    """
    Verifies 5-factor breakdown sum matches total estimated cost:
    total = material + labour + equipment + contractor OH&P + contingency
    """
    estimator = CostEstimator()
    res = estimator.estimate_repair_cost(
        defect_type="Pothole",
        severity="Medium",
        estimated_area_m2=0.6,
        is_calibrated=True,
        region="Default",
    )
    assert res["repair_required"] is True
    total = res["estimated_cost_inr"]
    breakdown = res["cost_breakdown"]

    component_sum = (
        breakdown["material_cost_inr"]
        + breakdown["labour_cost_inr"]
        + breakdown["equipment_cost_inr"]
        + breakdown["contractor_overhead_profit_inr"]
        + breakdown["contingency_and_safety_inr"]
    )
    assert math.isclose(total, component_sum, abs_tol=1.0)
    assert res["uncertainty_range"]["min_cost_inr"] < total < res["uncertainty_range"]["max_cost_inr"]


def test_cost_estimator_regional_rates_and_squaring():
    """Verifies Maharashtra 1.12x regional index and IRC 82 15% squaring cut allowance."""
    estimator = CostEstimator()
    base_res = estimator.estimate_repair_cost(
        defect_type="Pothole",
        severity="High",
        estimated_area_m2=1.0,
        region="Delhi",
    )
    mh_res = estimator.estimate_repair_cost(
        defect_type="Pothole",
        severity="High",
        estimated_area_m2=1.0,
        region="Maharashtra",
    )

    # Maharashtra cost index is 1.12 relative to Delhi 1.00
    assert mh_res["estimated_cost_inr"] > base_res["estimated_cost_inr"]
    ratio = mh_res["estimated_cost_inr"] / base_res["estimated_cost_inr"]
    assert math.isclose(ratio, 1.12, abs_tol=0.03)

    # Check 15% rectangular cut allowance note in assumptions
    assumptions_text = " ".join(base_res["estimation_assumptions"])
    assert "15%" in assumptions_text or "IRC:82" in assumptions_text


def test_cost_estimator_infrastructure_zero_cost():
    """Verifies that Traffic_Sign incurs zero road pavement repair cost."""
    estimator = CostEstimator()
    res = estimator.estimate_repair_cost(
        defect_type="Traffic_Sign",
        severity="N/A",
        estimated_area_m2=2.0,
    )
    assert res["estimated_cost_inr"] == 0.0
    assert res["repair_required"] is False
    assert res["cost_breakdown"]["material_cost_inr"] == 0.0


# ==========================================
# 5. DATABASE INTEGRITY & CONSTRAINT TESTS
# ==========================================

def test_database_user_role_check_constraint(db_session):
    """Ensures SQLite rejects invalid role strings not in ('admin', 'worker', 'user')."""
    invalid_user = User(
        username="hacker_role",
        password_hash="anyhash",
        role="super_admin",  # Violates CheckConstraint!
        is_active=True,
    )
    db_session.add(invalid_user)
    with pytest.raises(Exception):
        db_session.commit()
    db_session.rollback()


def test_database_defect_and_detection_result_relationship(db_session):
    """Verifies RoadDefect and DetectionResult foreign key linkage."""
    defect = RoadDefect(
        road_name="Test Expressway",
        defect_type="Pothole",
        severity="High",
        confidence=0.94,
        repair_cost=1800.0,
        is_defect=True,
    )
    db_session.add(defect)
    db_session.commit()
    db_session.refresh(defect)

    det = DetectionResult(
        defect_id=defect.id,
        class_id=0,
        class_name="Pothole",
        confidence=0.94,
        bbox_x1=100.0,
        bbox_y1=120.0,
        bbox_x2=200.0,
        bbox_y2=220.0,
        area_sqm=0.35,
        severity="High",
        is_defect=True,
    )
    db_session.add(det)
    db_session.commit()
    db_session.refresh(defect)

    assert len(defect.detections) == 1
    assert defect.detections[0].class_name == "Pothole"


def test_database_survey_and_gps_relationship(db_session):
    """Verifies Survey and GPSCoordinate foreign key relationship."""
    survey = Survey(
        road_name="State Highway 12",
        status="processing",
    )
    db_session.add(survey)
    db_session.commit()
    db_session.refresh(survey)

    gps = GPSCoordinate(
        survey_id=survey.id,
        latitude=18.5204,
        longitude=73.8567,
        elevation=560.0,
        speed_kmh=45.5,
    )
    db_session.add(gps)
    db_session.commit()
    db_session.refresh(survey)

    assert len(survey.gps_tracks) == 1
    assert survey.gps_tracks[0].latitude == 18.5204


# ==========================================
# 6. PYDANTIC SCHEMA INPUT VALIDATION TESTS
# ==========================================

def test_user_register_schema_validation():
    """Verifies UserRegister rejects short passwords or invalid usernames."""
    # Valid
    u = UserRegister(username="validuser", password="LongPassword123!")
    assert u.username == "validuser"

    # Password too short (<8)
    with pytest.raises(ValidationError):
        UserRegister(username="validuser", password="123")

    # Username too short (<3)
    with pytest.raises(ValidationError):
        UserRegister(username="ab", password="ValidPassword123!")


def test_user_create_admin_role_validation():
    """Verifies UserCreateAdmin validates allowed role strings."""
    # Valid
    adm = UserCreateAdmin(username="worker_bob", password="ValidPassword123!", role="worker")
    assert adm.role == "worker"

    # Invalid role
    with pytest.raises(ValidationError):
        UserCreateAdmin(username="worker_bob", password="ValidPassword123!", role="root")


def test_survey_create_schema_defaults():
    """Verifies SurveyCreate initializes proper defaults."""
    s = SurveyCreate(road_name="Ring Road")
    assert s.road_name == "Ring Road"
    assert s.start_chainage == 0.0
    assert s.end_chainage == 0.0
