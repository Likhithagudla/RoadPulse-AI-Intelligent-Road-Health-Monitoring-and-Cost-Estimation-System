from pathlib import Path
import sys
import torch
import torch.serialization

try:
    from ultralytics.nn.tasks import SegmentationModel, DetectionModel
    # add to safe globals
    torch.serialization.add_safe_globals([SegmentationModel, DetectionModel])
except Exception as e:
    print(f"Error adding safe globals: {e}")

from ultralytics import YOLO

try:
    model = YOLO(str(Path(__file__).resolve().parent.parent / "ai_models/weights/best.pt"))
    print("Model loaded successfully.")
    print("Model Names:", model.names)
except Exception as e:
    import traceback
    traceback.print_exc()
