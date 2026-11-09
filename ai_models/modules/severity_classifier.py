"""
RoadPulse AI - Pavement Distress Severity Classifier
Implements engineering-grade severity assessment based on IRC 82:2015 and ASTM D6433-20.
Evaluates physical defect dimensions, damage area, damage density (solidity),
and defect type, strictly decoupling AI detection confidence from physical structural severity.
"""

import math
from typing import Dict, Any, List, Optional


class SeverityClassifier:
    """
    Standardized pavement distress severity evaluation engine.
    """

    # Hazard weight factors per defect type (IRC 82:2015 guidelines)
    TYPE_HAZARD_WEIGHTS = {
        "Pothole": 1.5,             # High dynamic impact & tire puncture risk
        "Subsidence": 1.4,          # Structural subgrade failure
        "Rutting": 1.2,             # Hydroplaning and steering destabilization
        "Alligator_Cracking": 1.1,  # Structural fatigue failure of base course
        "Edge_Deterioration": 0.9,  # Shoulder loss & pavement edge drop-off
        "Cracking": 0.8,            # Water ingress precursor
        "Bleeding": 0.6,            # Loss of skid resistance
        "Fretting": 0.6,            # Surface binder loss
        "Repaired_Pothole": 0.4,    # Monitoring re-failure
        "Traffic_Sign": 0.0,        # Non-pavement infrastructure element
    }

    @staticmethod
    def classify_defect(
        defect_type: str,
        physical_area_m2: float,
        dimensions: Optional[Dict[str, Any]] = None,
        bbox: Optional[Dict[str, float]] = None,
        polygon: Optional[List[List[float]]] = None,
        ai_confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Computes physical structural severity independent of AI model confidence.
        
        Features evaluated:
        1. Physical surface area (m^2)
        2. Defect dimensions (equivalent diameter, length, width, aspect ratio)
        3. Damage density / Solidity (polygon area relative to bounding box)
        4. Defect structural category hazard weight
        """
        # Infrastructure items have no pavement distress severity
        if defect_type.lower() in ("traffic_sign", "guard_rail", "line_marking", "storm_drain"):
            return {
                "severity": "N/A",
                "severity_score": 0,
                "hazard_level": "Non-Distress",
                "ai_detection_confidence": round(ai_confidence, 4),
                "features_used": {"type": defect_type, "area_m2": 0.0},
                "justification": f"{defect_type} is an infrastructure asset, not a structural road defect.",
                "standard": "IRC:SP:73-2018 Road Infrastructure Inventory",
            }

        dims = dimensions or {}
        phys_length = dims.get("physical_length_m", 0.0)
        phys_width = dims.get("physical_width_m", 0.0)
        equiv_diam = dims.get("equivalent_diameter_m", 2.0 * math.sqrt(max(1e-6, physical_area_m2) / math.pi))

        # 1. Damage Density / Solidity:
        # Measures whether the damage is a solid, deep void (high density)
        # or a branching, diffuse crack network (low density).
        damage_density = 0.75  # Default assumption for pothole
        if bbox and "x1" in bbox:
            box_area_px = max(1.0, (bbox["x2"] - bbox["x1"]) * (bbox["y2"] - bbox["y1"]))
            if polygon and len(polygon) >= 3:
                import cv2
                import numpy as np
                poly_area_px = cv2.contourArea(np.array(polygon, dtype=np.float32))
                damage_density = min(1.0, max(0.05, poly_area_px / box_area_px))

        # 2. Aspect Ratio:
        aspect_ratio = (phys_length / max(0.05, phys_width)) if phys_width > 0 else 1.0

        # 3. Baseline Area Score (0 - 50 points)
        # Based on ASTM D6433 Pothole / Distress Area Scale
        if physical_area_m2 >= 0.50:
            area_score = 50.0
        elif physical_area_m2 >= 0.25:
            area_score = 35.0 + 15.0 * ((physical_area_m2 - 0.25) / 0.25)
        elif physical_area_m2 >= 0.08:
            area_score = 20.0 + 15.0 * ((physical_area_m2 - 0.08) / 0.17)
        else:
            area_score = max(5.0, 20.0 * (physical_area_m2 / 0.08))

        # 4. Dimension & Diameter Modifier (0 - 25 points)
        # Deep/large holes (diameter > 40cm) pose immediate rim/tire damage hazard
        dim_score = 0.0
        if equiv_diam >= 0.50:
            dim_score = 25.0
        elif equiv_diam >= 0.30:
            dim_score = 15.0 + 10.0 * ((equiv_diam - 0.30) / 0.20)
        else:
            dim_score = 15.0 * (equiv_diam / 0.30)

        # 5. Density Modifier (0 - 25 points)
        # High density = concentrated void / hole; Low density = surface spall
        density_score = damage_density * 25.0

        # Raw structural distress index (0 - 100)
        raw_score = area_score + dim_score + density_score

        # Apply defect type hazard weight
        hazard_weight = SeverityClassifier.TYPE_HAZARD_WEIGHTS.get(defect_type, 1.0)
        composite_score = min(100.0, raw_score * hazard_weight)

        # Categorize into ASTM / IRC 82 severity classes
        if composite_score >= 70.0 or physical_area_m2 >= 0.60 or equiv_diam >= 0.55:
            severity = "High"
            hazard_level = "Critical (Immediate Vehicle Suspension & Safety Hazard)"
        elif composite_score >= 35.0 or physical_area_m2 >= 0.12 or equiv_diam >= 0.30:
            severity = "Medium"
            hazard_level = "Moderate (Requires Maintenance Intervention Within 30 Days)"
        else:
            severity = "Low"
            hazard_level = "Minor (Routine Preventative Maintenance Recommended)"

        justification_points = [
            f"Physical Area: {physical_area_m2:.3f} m^2",
            f"Equivalent Diameter: {equiv_diam:.2f} m",
            f"Damage Density (Solidity): {damage_density:.1%}",
            f"Distress Severity Score: {composite_score:.1f}/100",
        ]

        return {
            "severity": severity,
            "severity_score": round(composite_score, 1),
            "hazard_level": hazard_level,
            "ai_detection_confidence": round(ai_confidence, 4),
            "features_used": {
                "defect_type": defect_type,
                "physical_area_m2": round(physical_area_m2, 4),
                "equivalent_diameter_m": round(equiv_diam, 3),
                "physical_length_m": round(phys_length, 3),
                "physical_width_m": round(phys_width, 3),
                "damage_density": round(damage_density, 3),
                "aspect_ratio": round(aspect_ratio, 2),
            },
            "justification": " | ".join(justification_points),
            "standard": "IRC 82:2015 (Road Maintenance) & ASTM D6433-20 (PCI)",
        }
