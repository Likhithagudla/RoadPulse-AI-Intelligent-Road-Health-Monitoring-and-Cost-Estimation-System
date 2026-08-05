import sys
from ultralytics import YOLO

model = YOLO("D:/Road_AI_Project/ai_models/weights/best.pt")
print("Model Names:", model.names)
