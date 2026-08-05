---
description: AI Model Enrichment & Improvement Process
---

This workflow guides you through the process of "Enriching" the AI model to fix missing detections and improve overall accuracy.

### 1. Identify Missing Defects
Analyze the photos where the AI "missed" a pothole or manhole. Save these images in a separate folder (e.g., `ai_models/dataset/missed_samples`).

### 2. Labeling (Enrichment)
Use a labeling tool (like LabelImg or Roboflow) to draw boxes around the missing defects in those images. Ensure the class names match our standard list:
- Pothole, Manhole, Cracking, Traffic_Sign, etc.

### 3. Merge into Dataset
Copy the new images and their label `.txt` files into the training directory:
- Images: `d:\Road_AI_Project\ai_models\dataset\unified\images\train`
- Labels: `d:\Road_AI_Project\ai_models\dataset\unified\labels\train`

### 4. Run Deep Enrichment Training
Once the new data is added, run the upgraded training pipeline:
// turbo
```powershell
python d:\Road_AI_Project\ai_models\scripts\train_model.py --mode train
```

### 5. Verify & Export
After training finishes (50 epochs recommended):
1.  Check `runs/road_defect_TIMESTAMP/results.png` to ensure the "Loss" went down.
2.  Export the new best model to the app:
// turbo
```powershell
python d:\Road_AI_Project\ai_models\scripts\train_model.py --mode export
```

### 6. Restart Backend
Restart your `run_server.bat` to begin using the newly enriched "brain."
