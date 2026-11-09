"""
RoadPulse AI - Configuration & Environment Loader
Handles dynamic path resolution, device detection, reproducible random seeds,
and standardized class/SOR configurations.
"""

import os
import random
import yaml
import numpy as np
import torch
from pathlib import Path
from typing import Dict, Any, Optional

# Base directories
MODULES_DIR = Path(__file__).resolve().parent
AI_MODELS_DIR = MODULES_DIR.parent
PROJECT_ROOT = AI_MODELS_DIR.parent

DATASET_DIR = AI_MODELS_DIR / "dataset" / "unified"
DATASET_YAML = DATASET_DIR / "data.yaml"
CONFIG_YAML = AI_MODELS_DIR / "config.yaml"
WEIGHTS_DIR = AI_MODELS_DIR / "weights"
DEFAULT_WEIGHTS = WEIGHTS_DIR / "best.pt"
RUNS_DIR = AI_MODELS_DIR / "runs"
EXPORT_DIR = AI_MODELS_DIR / "exported_models"

# 14-class full schema
FULL_CLASSES = {
    0: "Pothole",
    1: "Edge_Deterioration",
    2: "Alligator_Cracking",
    3: "Rutting",
    4: "Subsidence",
    5: "Cracking",
    6: "Bleeding",
    7: "Fretting",
    8: "Repaired_Pothole",
    9: "Line_Marking",
    10: "Storm_Drain",
    11: "Manhole",
    12: "Guard_Rail",
    13: "Traffic_Sign"
}

# The ground-truth active classes present in annotations
ACTIVE_ANNOTATED_CLASSES = {
    0: "Pothole",
    13: "Traffic_Sign"
}

# Schedule of Rates (SOR) per defect and severity (IRC / MORTH rates)
SOR_RATES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "Pothole": {
        "Low":    {"rate_per_sqm": 350,  "desc": "Cold mix patching"},
        "Medium": {"rate_per_sqm": 550,  "desc": "Hot mix patching"},
        "High":   {"rate_per_sqm": 850,  "desc": "Deep repair with granular base course"},
    },
    "Edge_Deterioration": {
        "Low":    {"rate_per_sqm": 250,  "desc": "Edge seal coating"},
        "Medium": {"rate_per_sqm": 450,  "desc": "Edge patching and levelling"},
        "High":   {"rate_per_sqm": 750,  "desc": "Edge reconstruction"},
    },
    "Alligator_Cracking": {
        "Low":    {"rate_per_sqm": 200,  "desc": "Polymer crack sealing"},
        "Medium": {"rate_per_sqm": 600,  "desc": "Surface overlay patching"},
        "High":   {"rate_per_sqm": 1200, "desc": "Full-depth asphalt reclamation"},
    },
    "Rutting": {
        "Low":    {"rate_per_sqm": 300,  "desc": "Surface leveling"},
        "Medium": {"rate_per_sqm": 700,  "desc": "Milling and hot-mix overlay"},
        "High":   {"rate_per_sqm": 1500, "desc": "Full pavement reconstruction"},
    },
    "Subsidence": {
        "Low":    {"rate_per_sqm": 400,  "desc": "Surface leveling"},
        "Medium": {"rate_per_sqm": 900,  "desc": "Sub-base stabilization"},
        "High":   {"rate_per_sqm": 2000, "desc": "Deep sub-base rebuilding"},
    },
    "Cracking": {
        "Low":    {"rate_per_sqm": 150,  "desc": "Crack routing and elastomeric filling"},
        "Medium": {"rate_per_sqm": 400,  "desc": "Routing, sealing, and slurry seal"},
        "High":   {"rate_per_sqm": 800,  "desc": "Full overlay application"},
    },
    "Bleeding": {
        "Low":    {"rate_per_sqm": 100,  "desc": "Sand blotting and rolling"},
        "Medium": {"rate_per_sqm": 300,  "desc": "Micro-surfacing"},
        "High":   {"rate_per_sqm": 600,  "desc": "Resurfacing with coarse aggregate"},
    },
    "Fretting": {
        "Low":    {"rate_per_sqm": 200,  "desc": "Fog seal application"},
        "Medium": {"rate_per_sqm": 450,  "desc": "Surface dressing"},
        "High":   {"rate_per_sqm": 800,  "desc": "Surface course replacement"},
    },
    "Repaired_Pothole": {
        "Low":    {"rate_per_sqm": 100,  "desc": "Inspection and monitoring only"},
        "Medium": {"rate_per_sqm": 350,  "desc": "Joint re-sealing"},
        "High":   {"rate_per_sqm": 650,  "desc": "Complete re-patching"},
    },
    "Traffic_Sign": {
        "Low":    {"rate_per_sqm": 0,    "desc": "Infrastructure: Informational Sign"},
        "Medium": {"rate_per_sqm": 0,    "desc": "Infrastructure: Cautionary Sign"},
        "High":   {"rate_per_sqm": 0,    "desc": "Infrastructure: Mandatory Sign"},
    },
}

# Aliases
SOR_RATES["pothole"] = SOR_RATES["Pothole"]
SOR_RATES["traffic_sign"] = SOR_RATES["Traffic_Sign"]


def set_seed(seed: int = 42) -> None:
    """Set random seed across all libraries for deterministic execution."""
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def get_device(preferred: Optional[str] = None) -> str:
    """Resolve compute device: prefers CUDA if available, falls back to CPU."""
    if preferred:
        pref = preferred.lower()
        if pref in ("cuda", "gpu") and torch.cuda.is_available():
            return "cuda"
        if pref == "cpu":
            return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


def patch_torch_load() -> None:
    """
    Patches torch.load for PyTorch 2.6+ to allow Ultralytics checkpoint loading
    without blocking on weights_only=True security check.
    """
    _orig = torch.load
    def _safe_load(*args, **kwargs):
        kwargs["weights_only"] = False
        return _orig(*args, **kwargs)
    torch.load = _safe_load


def ensure_dataset_yaml_path() -> Path:
    """
    Ensures dataset data.yaml points to the actual local unified directory
    instead of any obsolete hardcoded path.
    """
    yaml_path = DATASET_YAML
    if not yaml_path.exists():
        raise FileNotFoundError(f"data.yaml not found at {yaml_path}")
    
    with open(yaml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    # Set canonical local path using forward slashes for cross-platform compatibility
    current_path = str(DATASET_DIR.resolve()).replace("\\", "/")
    if cfg.get("path") != current_path:
        cfg["path"] = current_path
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, sort_keys=False)
            
    # Also update config.yaml if present
    if CONFIG_YAML.exists():
        with open(CONFIG_YAML, "r", encoding="utf-8") as f:
            ccfg = yaml.safe_load(f)
        if ccfg.get("path") != current_path:
            ccfg["path"] = current_path
            with open(CONFIG_YAML, "w", encoding="utf-8") as f:
                yaml.dump(ccfg, f, sort_keys=False)

    return yaml_path
