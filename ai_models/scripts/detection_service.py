"""
RoadPulse AI - Detection Service (Compatibility Adapter)
Bridges existing backend imports with the modularized ai_models.modules package.
"""

import sys
from pathlib import Path

# Add ai_models root to python path
AI_ROOT = Path(__file__).resolve().parent.parent
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from modules.config_loader import (
    SOR_RATES,
    FULL_CLASSES,
    ACTIVE_ANNOTATED_CLASSES,
    DEFAULT_WEIGHTS,
)
from modules.detector import (
    RoadDefectDetector,
    get_detector,
)

# Export symbols expected by backend
__all__ = [
    "SOR_RATES",
    "FULL_CLASSES",
    "ACTIVE_ANNOTATED_CLASSES",
    "DEFAULT_WEIGHTS",
    "RoadDefectDetector",
    "get_detector",
]
