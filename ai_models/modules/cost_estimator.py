"""
RoadPulse AI - Pavement Maintenance Cost Estimation Service
Authoritative, configurable civil engineering repair cost estimator based on
CPWD Delhi Schedule of Rates (DSR), MoRTH Section 3000, and IRC 82:2015.

Features:
- Configurable regional Schedule of Rates (SOR)
- Detailed 5-factor breakdown: Materials, Labour, Equipment, Contractor OH&P, Contingency
- Regional cost indices (Delhi, Maharashtra, Karnataka, Tamil Nadu, etc.)
- Strict uncertainty range computation
- Explicit engineering disclaimers distinguishing calibrated vs uncalibrated estimates
"""

import math
from functools import lru_cache
from typing import Dict, Any, List, Optional


class CostEstimator:
    """
    Civil engineering repair cost estimation engine.
    """

    # Regional cost indices relative to CPWD Delhi benchmark (1.00)
    REGIONAL_INDICES: Dict[str, float] = {
        "delhi": 1.00,
        "ncr": 1.00,
        "maharashtra": 1.12,
        "mumbai": 1.15,
        "pune": 1.10,
        "karnataka": 1.08,
        "bengaluru": 1.10,
        "tamil nadu": 1.05,
        "chennai": 1.07,
        "gujarat": 1.02,
        "ahmedabad": 1.03,
        "telangana": 1.04,
        "hyderabad": 1.06,
        "west bengal": 0.98,
        "kolkata": 1.00,
        "uttar pradesh": 0.96,
        "default": 1.00,
    }

    # Authoritative Schedule of Rates per defect type and severity (Base rates in INR per m^2)
    # References: MoRTH Section 3000 / 500, IRC:82-2015, CPWD DSR Road Work Section 16
    DEFAULT_SOR: Dict[str, Dict[str, Dict[str, Any]]] = {
        "Pothole": {
            "Low": {
                "base_rate_sqm": 380.0,
                "description": "Emergency cold mix bituminous patching (< 25 mm depth)",
                "material_pct": 0.50,
                "labour_pct": 0.28,
                "equipment_pct": 0.12,
                "specification": "IRC:116-2014 / MoRTH Cl. 3004.2",
            },
            "Medium": {
                "base_rate_sqm": 620.0,
                "description": "Hot mix asphalt patching with emulsion tack coat (25 - 50 mm depth)",
                "material_pct": 0.52,
                "labour_pct": 0.25,
                "equipment_pct": 0.13,
                "specification": "MoRTH Section 500 & Cl. 3004.3",
            },
            "High": {
                "base_rate_sqm": 980.0,
                "description": "Deep patch repair including sub-base re-compaction & bituminous concrete (> 50 mm depth)",
                "material_pct": 0.55,
                "labour_pct": 0.22,
                "equipment_pct": 0.13,
                "specification": "IRC:82-2015 Section 4.2 / MoRTH Cl. 3004.4",
            },
        },
        "Edge_Deterioration": {
            "Low": {
                "base_rate_sqm": 260.0,
                "description": "Pavement edge seal coating and minor leveling",
                "material_pct": 0.45,
                "labour_pct": 0.35,
                "equipment_pct": 0.10,
                "specification": "IRC:82-2015 Cl. 5.3",
            },
            "Medium": {
                "base_rate_sqm": 480.0,
                "description": "Edge cutting, tack coat, and asphalt leveling course",
                "material_pct": 0.50,
                "labour_pct": 0.30,
                "equipment_pct": 0.10,
                "specification": "MoRTH Section 500",
            },
            "High": {
                "base_rate_sqm": 820.0,
                "description": "Complete shoulder and edge reconstruction with granular sub-base",
                "material_pct": 0.54,
                "labour_pct": 0.26,
                "equipment_pct": 0.10,
                "specification": "MoRTH Cl. 401 & 507",
            },
        },
        "Alligator_Cracking": {
            "Low": {
                "base_rate_sqm": 220.0,
                "description": "High-viscosity polymer modified crack sealing",
                "material_pct": 0.48,
                "labour_pct": 0.32,
                "equipment_pct": 0.10,
                "specification": "IRC:SP:81-2019",
            },
            "Medium": {
                "base_rate_sqm": 650.0,
                "description": "Milling surface distress and applying micro-surfacing overlay",
                "material_pct": 0.53,
                "labour_pct": 0.24,
                "equipment_pct": 0.13,
                "specification": "IRC:SP:81-2019 / MoRTH Cl. 514",
            },
            "High": {
                "base_rate_sqm": 1350.0,
                "description": "Full-depth structural asphalt replacement and sub-base stabilization",
                "material_pct": 0.58,
                "labour_pct": 0.20,
                "equipment_pct": 0.12,
                "specification": "IRC:37-2018 / MoRTH Section 500",
            },
        },
        "Rutting": {
            "Low": {
                "base_rate_sqm": 320.0,
                "description": "Cold milling high spots and longitudinal leveling",
                "material_pct": 0.20,
                "labour_pct": 0.35,
                "equipment_pct": 0.35,
                "specification": "MoRTH Cl. 517",
            },
            "Medium": {
                "base_rate_sqm": 750.0,
                "description": "Milling 40mm wearing course and dense bituminous overlay",
                "material_pct": 0.52,
                "labour_pct": 0.22,
                "equipment_pct": 0.16,
                "specification": "MoRTH Cl. 505 & 507",
            },
            "High": {
                "base_rate_sqm": 1650.0,
                "description": "Full depth pavement trenching, sub-base rebuilding, and heavy-duty overlay",
                "material_pct": 0.56,
                "labour_pct": 0.20,
                "equipment_pct": 0.14,
                "specification": "IRC:37-2018",
            },
        },
        "Subsidence": {
            "Low": {
                "base_rate_sqm": 420.0,
                "description": "Corrective surface leveling course",
                "material_pct": 0.50,
                "labour_pct": 0.30,
                "equipment_pct": 0.10,
                "specification": "MoRTH Section 500",
            },
            "Medium": {
                "base_rate_sqm": 950.0,
                "description": "Subgrade stabilization, drainage correction, and bituminous patching",
                "material_pct": 0.52,
                "labour_pct": 0.25,
                "equipment_pct": 0.13,
                "specification": "IRC:82-2015 Section 6",
            },
            "High": {
                "base_rate_sqm": 2200.0,
                "description": "Deep subgrade excavation, geotextile installation, WMM base & BC rebuilding",
                "material_pct": 0.55,
                "labour_pct": 0.22,
                "equipment_pct": 0.13,
                "specification": "MoRTH Section 300 & 400",
            },
        },
        "Cracking": {
            "Low": {
                "base_rate_sqm": 160.0,
                "description": "Compressed air cleaning and elastomeric sealant injection",
                "material_pct": 0.45,
                "labour_pct": 0.38,
                "equipment_pct": 0.07,
                "specification": "IRC:82-2015 Cl. 4.1",
            },
            "Medium": {
                "base_rate_sqm": 420.0,
                "description": "Mechanical crack routing, rubberized asphalt sealant, and slurry seal",
                "material_pct": 0.48,
                "labour_pct": 0.32,
                "equipment_pct": 0.10,
                "specification": "MoRTH Cl. 513",
            },
            "High": {
                "base_rate_sqm": 850.0,
                "description": "Geotextile paving fabric application and 30mm bituminous concrete overlay",
                "material_pct": 0.55,
                "labour_pct": 0.25,
                "equipment_pct": 0.10,
                "specification": "IRC:SP:81-2019",
            },
        },
        "Bleeding": {
            "Low": {
                "base_rate_sqm": 110.0,
                "description": "Application of heated dry coarse sand / stone dust and rolling",
                "material_pct": 0.35,
                "labour_pct": 0.40,
                "equipment_pct": 0.15,
                "specification": "IRC:82-2015 Cl. 4.4",
            },
            "Medium": {
                "base_rate_sqm": 320.0,
                "description": "Micro-surfacing application with polymer modified emulsion",
                "material_pct": 0.52,
                "labour_pct": 0.28,
                "equipment_pct": 0.10,
                "specification": "MoRTH Cl. 514",
            },
            "High": {
                "base_rate_sqm": 650.0,
                "description": "Surface planing / milling excess binder and applying surface dressing",
                "material_pct": 0.48,
                "labour_pct": 0.27,
                "equipment_pct": 0.15,
                "specification": "MoRTH Cl. 510",
            },
        },
        "Fretting": {
            "Low": {
                "base_rate_sqm": 210.0,
                "description": "Fog seal rejuvenator spray",
                "material_pct": 0.55,
                "labour_pct": 0.25,
                "equipment_pct": 0.10,
                "specification": "IRC:82-2015 Cl. 4.3",
            },
            "Medium": {
                "base_rate_sqm": 460.0,
                "description": "Single coat bituminous surface dressing with 10mm chippings",
                "material_pct": 0.54,
                "labour_pct": 0.28,
                "equipment_pct": 0.08,
                "specification": "MoRTH Cl. 509",
            },
            "High": {
                "base_rate_sqm": 820.0,
                "description": "25mm Bituminous Concrete renewal course",
                "material_pct": 0.56,
                "labour_pct": 0.24,
                "equipment_pct": 0.10,
                "specification": "MoRTH Cl. 507",
            },
        },
        "Repaired_Pothole": {
            "Low": {
                "base_rate_sqm": 0.0,
                "description": "Distress healed / monitoring only; zero immediate expenditure required",
                "material_pct": 0.0,
                "labour_pct": 0.0,
                "equipment_pct": 0.0,
                "specification": "IRC:82-2015 Routine Maintenance Inspection",
            },
            "Medium": {
                "base_rate_sqm": 360.0,
                "description": "Joint crack resealing around previously patched perimeter",
                "material_pct": 0.48,
                "labour_pct": 0.36,
                "equipment_pct": 0.06,
                "specification": "IRC:82-2015 Section 4",
            },
            "High": {
                "base_rate_sqm": 720.0,
                "description": "Full cutout and re-patching of failed joint / perimeter cracking",
                "material_pct": 0.52,
                "labour_pct": 0.28,
                "equipment_pct": 0.10,
                "specification": "MoRTH Cl. 3004",
            },
        },
        "Traffic_Sign": {
            "Low": {
                "base_rate_sqm": 0.0,
                "description": "Informational Sign Asset (No road distress repair cost)",
                "material_pct": 0.0,
                "labour_pct": 0.0,
                "equipment_pct": 0.0,
                "specification": "IRC:67-2012 Code of Practice for Road Signs",
            },
            "Medium": {
                "base_rate_sqm": 0.0,
                "description": "Cautionary Sign Asset (No road distress repair cost)",
                "material_pct": 0.0,
                "labour_pct": 0.0,
                "equipment_pct": 0.0,
                "specification": "IRC:67-2012 Code of Practice for Road Signs",
            },
            "High": {
                "base_rate_sqm": 0.0,
                "description": "Mandatory / Regulatory Sign Asset (No road distress repair cost)",
                "material_pct": 0.0,
                "labour_pct": 0.0,
                "equipment_pct": 0.0,
                "specification": "IRC:67-2012 Code of Practice for Road Signs",
            },
        },
    }

    # Standard CPWD / PWD Markups
    CONTRACTOR_OVERHEAD_AND_PROFIT_PCT = 0.14  # Standard CPWD 14% on prime cost
    CONTINGENCY_AND_SAFETY_PCT = 0.06          # Traffic management, sign boards, safety barriers (6%)
    MINIMUM_PATCH_AREA_M2 = 0.18               # Practical minimum rectangular cut area (IRC 82 rectangular rule)
    MINIMUM_MOBILIZATION_INR = 250.0           # Minimum mobilization / setup charge per intervention

    def __init__(self, regional_rates: Optional[Dict[str, Any]] = None):
        self.sor = self.DEFAULT_SOR.copy()
        if regional_rates:
            for k, v in regional_rates.items():
                if k in self.sor:
                    self.sor[k].update(v)
                else:
                    self.sor[k] = v

    @classmethod
    @lru_cache(maxsize=32)
    def get_regional_multiplier(cls, region_name: str) -> float:
        """Resolves region cost multiplier (case-insensitive) with LRU caching."""
        key = region_name.strip().lower() if region_name else "default"
        return cls.REGIONAL_INDICES.get(key, 1.00)

    def estimate_repair_cost(
        self,
        defect_type: str,
        severity: str,
        estimated_area_m2: float,
        is_calibrated: bool = True,
        region: str = "Default",
        confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Calculates comprehensive civil engineering repair cost estimate.
        
        Args:
            defect_type: Name of defect (e.g. 'Pothole', 'Edge_Deterioration', 'Traffic_Sign')
            severity: Severity tier ('Low', 'Medium', 'High', or 'N/A')
            estimated_area_m2: Physical area in square meters
            is_calibrated: Whether perspective camera calibration was verified
            region: Regional location name (e.g. 'Delhi', 'Maharashtra', 'Karnataka')
            confidence: AI model detection confidence score
            
        Returns:
            Dict containing estimated cost, full 5-factor breakdown, assumptions,
            uncertainty range, and engineering measurement disclaimers.
        """
        # Infrastructure elements (Traffic_Sign, Guard_Rail, etc.) have no pavement repair cost
        if defect_type.lower() in ("traffic_sign", "guard_rail", "line_marking", "storm_drain") or severity == "N/A":
            return {
                "estimated_cost_inr": 0.0,
                "currency": "INR",
                "repair_required": False,
                "defect_type": defect_type,
                "severity": severity,
                "repair_treatment": "Non-distress infrastructure asset; no road surface patching required.",
                "measurement_status": "NOT_APPLICABLE",
                "cost_breakdown": {
                    "material_cost_inr": 0.0,
                    "labour_cost_inr": 0.0,
                    "equipment_cost_inr": 0.0,
                    "contractor_overhead_profit_inr": 0.0,
                    "contingency_and_safety_inr": 0.0,
                },
                "uncertainty_range": {
                    "min_cost_inr": 0.0,
                    "max_cost_inr": 0.0,
                    "confidence_band": "N/A",
                },
                "estimation_assumptions": [
                    "Item is a highway infrastructure asset, not a structural pavement distress.",
                    "Asset inventory recorded per IRC:SP:73-2018.",
                ],
                "engineering_disclaimer": "No road surface repair works required for this asset.",
            }

        # Resolve SOR configuration
        canonical_type = defect_type
        if canonical_type not in self.sor:
            # Fallback to Pothole rates if unknown defect
            canonical_type = "Pothole"

        sev_key = severity if severity in self.sor[canonical_type] else "Medium"
        sor_entry = self.sor[canonical_type][sev_key]

        base_unit_rate = sor_entry["base_rate_sqm"]
        treatment_desc = sor_entry["description"]
        specification = sor_entry.get("specification", "IRC:82-2015")

        # Resolve regional index multiplier
        reg_mult = self.get_regional_multiplier(region)
        adjusted_unit_rate = round(base_unit_rate * reg_mult, 2)

        # Apply IRC:82 Section 4.2 Rectangular Squaring rule:
        # Potholes are always cut in rectangular shapes extending ~100mm beyond visible edges.
        # Thus, effective patch area is at least 15% larger than the raw visible defect area.
        effective_repair_area = max(self.MINIMUM_PATCH_AREA_M2, estimated_area_m2 * 1.15)
        effective_repair_area = round(effective_repair_area, 4)

        # Base prime cost (Materials + Labour + Equipment)
        raw_prime_cost = adjusted_unit_rate * effective_repair_area

        # 5-factor breakdown calculations
        mat_pct = sor_entry.get("material_pct", 0.50)
        lab_pct = sor_entry.get("labour_pct", 0.28)
        eqp_pct = sor_entry.get("equipment_pct", 0.12)

        material_cost = round(raw_prime_cost * mat_pct, 2)
        labour_cost = round(raw_prime_cost * lab_pct, 2)
        equipment_cost = round(raw_prime_cost * eqp_pct, 2)

        # Contractor overhead & profit (CPWD standard: 14% on prime cost)
        overhead_and_profit = round(raw_prime_cost * self.CONTRACTOR_OVERHEAD_AND_PROFIT_PCT, 2)

        # Contingency, traffic control, and safety barriers (6%)
        contingency_and_safety = round(raw_prime_cost * self.CONTINGENCY_AND_SAFETY_PCT, 2)

        total_cost = material_cost + labour_cost + equipment_cost + overhead_and_profit + contingency_and_safety

        # Minimum mobilization threshold
        if total_cost < self.MINIMUM_MOBILIZATION_INR and total_cost > 0.0:
            adjustment = self.MINIMUM_MOBILIZATION_INR - total_cost
            total_cost = self.MINIMUM_MOBILIZATION_INR
            contingency_and_safety = round(contingency_and_safety + adjustment, 2)

        total_cost = round(total_cost, 2)

        # Uncertainty bounds based on calibration status
        if is_calibrated:
            measurement_status = "CALIBRATED_GEOMETRIC_ESTIMATE"
            # +/- 15% to 20% variance standard in road patch estimation
            min_cost = round(total_cost * 0.85, 2)
            max_cost = round(total_cost * 1.20, 2)
            confidence_band = "Medium-High (Calibrated Camera Geometry)"
            disclaimer = (
                "Estimated repair cost derived from perspective ground-plane projection and regional SOR. "
                "Subject to on-site substrate depth measurement by a qualified highway engineer."
            )
        else:
            measurement_status = "UNVERIFIED_HEURISTIC_ESTIMATE"
            # Uncalibrated has high variance (-35% / +45%)
            min_cost = round(total_cost * 0.65, 2)
            max_cost = round(total_cost * 1.45, 2)
            confidence_band = "Low (Uncalibrated Optical Geometry - Wide Uncertainty Range)"
            disclaimer = (
                "CAUTION: Uncalibrated perspective geometry. This figure is an indicative AI estimate and "
                "MUST NEVER be presented as a verified engineering measurement for procurement, contractor billing, or legal tenders."
            )

        assumptions: List[str] = [
            f"Technical Specification: {specification}",
            f"Treatment: {treatment_desc}",
            f"Visible defect surface area: {round(estimated_area_m2, 4)} m^2",
            f"Effective rectangular cut area (with 15% IRC:82 edge squaring allowance): {effective_repair_area} m^2",
            f"Base SOR unit rate: INR {base_unit_rate}/m^2 (CPWD DSR Road Work benchmark)",
            f"Regional rate factor: {reg_mult:.2f} ({region.capitalize()} zone)",
            f"Adjusted unit rate: INR {adjusted_unit_rate}/m^2",
            f"Contractor overhead & profit: {int(self.CONTRACTOR_OVERHEAD_AND_PROFIT_PCT * 100)}% on prime cost",
            f"Contingency, safety signage & traffic marshals: {int(self.CONTINGENCY_AND_SAFETY_PCT * 100)}%",
        ]

        return {
            "estimated_cost_inr": total_cost,
            "currency": "INR",
            "repair_required": True,
            "defect_type": canonical_type,
            "severity": sev_key,
            "repair_treatment": treatment_desc,
            "specification": specification,
            "effective_patch_area_sqm": effective_repair_area,
            "measurement_status": measurement_status,
            "cost_breakdown": {
                "material_cost_inr": material_cost,
                "labour_cost_inr": labour_cost,
                "equipment_cost_inr": equipment_cost,
                "contractor_overhead_profit_inr": overhead_and_profit,
                "contingency_and_safety_inr": contingency_and_safety,
            },
            "cost_breakdown_percentages": {
                "materials_pct": round((material_cost / max(1.0, total_cost)) * 100, 1),
                "labour_pct": round((labour_cost / max(1.0, total_cost)) * 100, 1),
                "equipment_pct": round((equipment_cost / max(1.0, total_cost)) * 100, 1),
                "contractor_oh_p_pct": round((overhead_and_profit / max(1.0, total_cost)) * 100, 1),
                "contingency_safety_pct": round((contingency_and_safety / max(1.0, total_cost)) * 100, 1),
            },
            "uncertainty_range": {
                "min_cost_inr": min_cost,
                "max_cost_inr": max_cost,
                "confidence_band": confidence_band,
            },
            "regional_factor": {
                "region": region.capitalize(),
                "multiplier": reg_mult,
            },
            "estimation_assumptions": assumptions,
            "engineering_disclaimer": disclaimer,
        }
