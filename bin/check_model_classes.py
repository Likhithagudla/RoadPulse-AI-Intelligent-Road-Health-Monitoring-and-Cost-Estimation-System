import sys
import os
from ultralytics import YOLO

model_path = r'd:\Road_AI_Project\ai_models\weights\best.pt'
if not os.path.exists(model_path):
    print(f"Model not found at {model_path}")
else:
    model = YOLO(model_path)
    print("Model Classes (names):")
    print(model.names)
    print("\nModel configuration:")
    print(f"Confidence threshold in service: 0.02")
