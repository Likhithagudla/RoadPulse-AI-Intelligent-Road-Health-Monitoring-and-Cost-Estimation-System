"""
RoadPulse AI - Ground-Plane Perspective Geometry & Area Calibrator
Replaces fixed 3-metre road width assumptions with perspective projection,
ground-plane ray casting, and exact polygon mask integration.
"""

import math
import numpy as np
import cv2
from typing import Dict, Any, List, Optional, Tuple


class CameraParameters:
    """
    Optical and mounting geometry of a vehicle-mounted camera / smartphone.
    """
    def __init__(
        self,
        mount_height_m: float = 1.4,      # Typical smartphone / dashcam windshield mount height (meters)
        pitch_deg: float = 14.0,           # Downward tilt angle relative to horizon (degrees)
        fov_v_deg: float = 55.0,           # Vertical field of view (degrees)
        fov_h_deg: float = 70.0,           # Horizontal field of view (degrees)
        image_width: int = 1920,
        image_height: int = 1080,
    ):
        self.mount_height_m = mount_height_m
        self.pitch_deg = pitch_deg
        self.pitch_rad = math.radians(pitch_deg)
        self.fov_v_deg = fov_v_deg
        self.fov_h_deg = fov_h_deg
        self.image_width = image_width
        self.image_height = image_height

        # Principal point (optical center)
        self.cx = image_width / 2.0
        self.cy = image_height / 2.0

        # Focal lengths in pixels
        self.fy = (image_height / 2.0) / math.tan(math.radians(fov_v_deg / 2.0))
        self.fx = (image_width / 2.0) / math.tan(math.radians(fov_h_deg / 2.0))

        # Vanishing line (horizon row in image): where ground plane intersects infinity
        # v_horizon = cy - fy * tan(pitch)
        self.horizon_y = self.cy - self.fy * math.tan(self.pitch_rad)


class GeometryCalibrator:
    """
    Ground-plane metric reconstruction for road surface defects.
    Converts pixel bounding boxes and segmentation polygons into calibrated
    real-world dimensions (length, width, physical area in m^2).
    """

    def __init__(self, camera_params: Optional[CameraParameters] = None):
        self.params = camera_params or CameraParameters()

    def update_resolution(self, width: int, height: int) -> None:
        """Dynamically scales camera calibration to match input image resolution."""
        if width != self.params.image_width or height != self.params.image_height:
            self.params = CameraParameters(
                mount_height_m=self.params.mount_height_m,
                pitch_deg=self.params.pitch_deg,
                fov_v_deg=self.params.fov_v_deg,
                fov_h_deg=self.params.fov_h_deg,
                image_width=width,
                image_height=height,
            )

    def pixel_to_ground(self, u: float, v: float) -> Tuple[Optional[float], Optional[float], bool]:
        """
        Projects a single image pixel (u, v) onto the flat road ground plane (Y = -H).
        Returns: (X_meters, Z_meters, is_reliable)
          - X: Lateral distance from vehicle centerline (+ = right, - = left)
          - Z: Forward longitudinal distance ahead of vehicle bumper
        """
        # A pixel at or above horizon represents the sky or distant background
        if v <= self.params.horizon_y + 15.0:
            return None, None, False

        # Angle of ray relative to camera optical axis in pitch
        # delta_pitch = arctan((v - cy) / fy)
        # ray angle downwards relative to horizontal ground: alpha = pitch + delta_pitch
        delta_pitch = math.atan((v - self.params.cy) / self.params.fy)
        alpha = self.params.pitch_rad + delta_pitch

        if alpha <= math.radians(1.5):  # Graze angle too shallow, perspective foreshortening extreme
            return None, None, False

        # Forward distance on ground plane
        z = self.params.mount_height_m / math.tan(alpha)

        # Foreshortening limit: beyond 45 meters, pixel resolution is insufficient for defect measurement
        if z <= 0.5 or z > 45.0:
            return None, None, False

        # Lateral distance on ground plane
        # ray angle in yaw: delta_yaw = arctan((u - cx) / fx)
        # x = z * tan(delta_yaw) = z * (u - cx) / fx
        x = z * (u - self.params.cx) / self.params.fx

        return x, z, True

    def calculate_polygon_area_m2(self, polygon_pixels: List[List[float]]) -> Tuple[float, Dict[str, Any]]:
        """
        Computes true ground surface area by transforming each polygon vertex
        to real-world coordinates (X, Z) and applying Green's theorem (shoelace formula).
        """
        if not polygon_pixels or len(polygon_pixels) < 3:
            return 0.0, {
                "method": "insufficient_polygon_vertices",
                "is_calibrated": False,
                "confidence_level": "none",
                "reason": "Fewer than 3 polygon vertices provided",
            }

        ground_coords: List[Tuple[float, float]] = []
        unreliable_points = 0

        for pt in polygon_pixels:
            u, v = float(pt[0]), float(pt[1])
            x, z, reliable = self.pixel_to_ground(u, v)
            if reliable and x is not None and z is not None:
                ground_coords.append((x, z))
            else:
                unreliable_points += 1

        # If more than 30% of points are above horizon or graze angle, mark estimate as uncalibrated
        if len(ground_coords) < 3 or (unreliable_points / len(polygon_pixels)) > 0.30:
            # Fall back to adaptive heuristic
            return self._fallback_area_heuristic(polygon_pixels, is_polygon=True)

        # Shoelace formula for physical area in m^2 on the ground plane (X, Z)
        n = len(ground_coords)
        area_sum = 0.0
        for i in range(n):
            j = (i + 1) % n
            area_sum += ground_coords[i][0] * ground_coords[j][1]
            area_sum -= ground_coords[j][0] * ground_coords[i][1]
        phys_area_m2 = abs(area_sum) / 2.0

        # Physical dimensions
        xs = [pt[0] for pt in ground_coords]
        zs = [pt[1] for pt in ground_coords]
        phys_width_m = max(xs) - min(xs)
        phys_length_m = max(zs) - min(zs)
        avg_distance_m = sum(zs) / len(zs)

        # Equivalent circular diameter
        equiv_diam_m = 2.0 * math.sqrt(max(1e-6, phys_area_m2) / math.pi)

        return round(phys_area_m2, 4), {
            "method": "ground_plane_homography_mask",
            "is_calibrated": True,
            "confidence_level": "high" if avg_distance_m < 18.0 else "medium",
            "physical_length_m": round(phys_length_m, 3),
            "physical_width_m": round(phys_width_m, 3),
            "equivalent_diameter_m": round(equiv_diam_m, 3),
            "mean_camera_distance_m": round(avg_distance_m, 2),
            "unreliable_fraction": round(unreliable_points / len(polygon_pixels), 2),
            "notes": "Exact Green-theorem integration on calibrated ground-plane projection",
        }

    def calculate_bbox_area_m2(self, bbox: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculates ground-plane area from bounding box corners when segmentation mask is absent.
        Accounts for vertical perspective compression between top edge (y1) and bottom edge (y2).
        """
        x1, y1 = float(bbox["x1"]), float(bbox["y1"])
        x2, y2 = float(bbox["x2"]), float(bbox["y2"])

        # Project 4 corners
        x_bl, z_bottom, rel_b1 = self.pixel_to_ground(x1, y2)
        x_br, _, rel_b2 = self.pixel_to_ground(x2, y2)
        x_tl, z_top, rel_t1 = self.pixel_to_ground(x1, y1)
        x_tr, _, rel_t2 = self.pixel_to_ground(x2, y1)

        if not (rel_b1 and rel_b2 and rel_t1 and rel_t2):
            return self._fallback_area_heuristic([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], is_polygon=False)

        # Ground trapezoid dimensions
        width_near_m = abs(x_br - x_bl)
        width_far_m = abs(x_tr - x_tl)
        avg_width_m = (width_near_m + width_far_m) / 2.0
        length_m = abs(z_top - z_bottom)

        # Bounding box is an upper bound; apply standard form factor (0.785 for elliptical/pothole defects)
        form_factor = 0.785
        phys_area_m2 = avg_width_m * length_m * form_factor
        avg_distance_m = (z_bottom + z_top) / 2.0

        return round(phys_area_m2, 4), {
            "method": "ground_plane_homography_bbox",
            "is_calibrated": True,
            "confidence_level": "medium",
            "physical_length_m": round(length_m, 3),
            "physical_width_m": round(avg_width_m, 3),
            "equivalent_diameter_m": round(2.0 * math.sqrt(max(1e-6, phys_area_m2) / math.pi), 3),
            "mean_camera_distance_m": round(avg_distance_m, 2),
            "notes": "Trapezoidal perspective ground-plane projection with 0.785 ellipse form factor",
        }

    def _fallback_area_heuristic(self, points: List[List[float]], is_polygon: bool) -> Tuple[float, Dict[str, Any]]:
        """
        Adaptive fallback when camera pitch/height or graze angle prevents exact homography.
        Uses depth-attenuated polynomial scaling based on vertical frame position (v/H).
        Clearly flags the estimate as uncalibrated heuristic with uncertainty bounds.
        """
        ys = [p[1] for p in points]
        xs = [p[0] for p in points]
        y_bottom = max(ys)
        h_frame = self.params.image_height
        w_frame = self.params.image_width

        # Relative vertical position from bottom (0 = bottom bumper, 1 = top horizon)
        rel_pos = max(0.0, min(1.0, (h_frame - y_bottom) / h_frame))

        # Quadratic perspective scaling: near bottom 1 pixel = ~2mm, near center 1 pixel = ~12mm
        # scale_m_per_pixel = 0.0025 + 0.015 * (rel_pos ** 1.8)
        scale = 0.0025 + 0.018 * (rel_pos ** 1.8)

        if is_polygon and len(points) >= 3:
            pts_array = np.array(points, dtype=np.float32)
            pixel_area = cv2.contourArea(pts_array)
        else:
            pixel_area = (max(xs) - min(xs)) * (max(ys) - min(ys)) * 0.785

        est_area_m2 = pixel_area * (scale ** 2)

        return round(est_area_m2, 4), {
            "method": "depth_attenuated_heuristic_fallback",
            "is_calibrated": False,
            "confidence_level": "low",
            "uncertainty_margin": "+/- 40%",
            "reason": "Defect located near horizon or optical calibration unverified",
            "notes": "Uncalibrated heuristic estimate. Cannot be treated as verified engineering measurement.",
        }
