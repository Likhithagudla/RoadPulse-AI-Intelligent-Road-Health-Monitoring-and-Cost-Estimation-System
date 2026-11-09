from pathlib import Path
import sys
from ultralytics import YOLO

model = YOLO(str(Path(__file__).resolve().parent.parent / "ai_models/weights/best.pt"))
print("Model Names:", model.names)
