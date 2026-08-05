"""
============================================================
Road AI - YOLOv8 Model Training Pipeline
============================================================
This is the MAIN training script. It handles:
1. Loading the dataset configuration
2. Training a YOLOv8 model for road defect detection
3. Validating the model
4. Exporting to ONNX for deployment
5. Running inference on test images

Usage:
    python train_model.py --mode train      # Train the model
    python train_model.py --mode validate   # Validate existing model
    python train_model.py --mode export     # Export to ONNX
    python train_model.py --mode test       # Run inference on test images
    python train_model.py --mode full       # Do everything
"""

import os
import sys
import argparse
import yaml
import json
import shutil
from pathlib import Path
from datetime import datetime
import ctypes

def prevent_sleep():
    """Prevents Windows from entering sleep mode."""
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        print("\n[INFO] 🛑 Windows sleep mode has been disabled for the duration of the run!")
    except:
        pass

def allow_sleep():
    """Restores Windows sleep mode restrictions."""
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
    except:
        pass

# ===================== CONFIGURATION =====================

ROOT = "D:/Road_AI_Project/ai_models"
CONFIG_PATH = os.path.join(ROOT, "config.yaml")
WEIGHTS_DIR = os.path.join(ROOT, "weights")
RUNS_DIR = os.path.join(ROOT, "runs")
EXPORT_DIR = os.path.join(ROOT, "exported_models")

# Training Hyperparameters (Enriched Configuration)
TRAINING_CONFIG = {
    "model": "yolov8s-seg.pt",     # Upgraded to Instance Segmentation model
    "epochs": 50,              # Full enrichment training
    "batch": 4,                # Lower batch for YOLOv8s on CPU
    "imgsz": 640,              # Increased to 640 for high accuracy on small cracks
    "patience": 20,
    "optimizer": "AdamW",
    "lr0": 0.001,
    "lrf": 0.01,
    "warmup_epochs": 5,
    "warmup_momentum": 0.8,
    "weight_decay": 0.0005,
    "box": 7.5,
    "cls": 0.5,
    "hsv_h": 0.015,
    "hsv_s": 0.7,
    "hsv_v": 0.4,
    "degrees": 10.0,           # Increased rotation
    "translate": 0.1,
    "scale": 0.5,
    "flipud": 0.2,
    "fliplr": 0.5,
    "mosaic": 1.0,             # Full mosaic augmentation
    "mixup": 0.2,              # Increased mixup for better generalization
    "copy_paste": 0.2,         # Increased copy-paste for defect diversity
}

os.makedirs(WEIGHTS_DIR, exist_ok=True)
os.makedirs(RUNS_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)


# ===================== TRAINING =====================

def train_model(resume=False, model_path=None):
    """Train the YOLOv8 model for road defect detection."""
    from ultralytics import YOLO
    
    print("=" * 60)
    print("  Road AI - Model Training")
    print("=" * 60)
    
    # Verify dataset exists
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    
    train_dir = os.path.join(config['path'], 'images', 'train')
    if not os.path.exists(train_dir) or len(os.listdir(train_dir)) == 0:
        print("[ERROR] Training data not found!")
        print(f"Expected at: {train_dir}")
        print("Run prepare_dataset.py first!")
        return None
    
    n_train = len(os.listdir(train_dir))
    print(f"[OK] Found {n_train} training images")
    
    # Adjust batch size based on image count
    batch = min(TRAINING_CONFIG['batch'], max(2, n_train // 4))
    
    # Start training
    if resume:
        if model_path and os.path.exists(model_path):
            print(f"\n[1/4] Resuming training from: {model_path}")
            model = YOLO(model_path)
            run_name = os.path.basename(os.path.dirname(os.path.dirname(model_path)))
        else:
            last_weights = os.path.join(WEIGHTS_DIR, "last.pt")
            if not os.path.exists(last_weights):
                print("[ERROR] Cannot resume - last.pt not found in weights directory!")
                return None
            print(f"\n[1/4] Resuming training from: {last_weights}")
            model = YOLO(last_weights)
            # Find the original run directory if possible
            # For simplicity, we'll assume we want to resume the run that created this last.pt
            run_name = "road_defect_resumed" 
        
        print(f"[2/4] Resuming training: {run_name}")
        prevent_sleep()
        try:
            # Optimized for CPU/RAM as no dedicated NVIDIA GPU was found
            results = model.train(
                resume=True,
                workers=4,        # Use 4 CPU cores for data loading (safe for Windows)
                cache=True,       # Cache images in RAM (you have 14GB free)
            )
        finally:
            allow_sleep()
    else:
        # Load pre-trained model
        model_name = model_path if model_path else TRAINING_CONFIG['model']
        print(f"\n[1/4] Loading pre-trained model: {model_name}")
        model = YOLO(model_name)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_name = f"road_defect_{timestamp}"
        
        print(f"[2/4] Starting training: {run_name}")
        print(f"      Epochs: {TRAINING_CONFIG['epochs']}")
        print(f"      Batch:  {batch}")
        print(f"      ImgSz:  {TRAINING_CONFIG['imgsz']}")
        print()
        
        prevent_sleep()
        try:
            results = model.train(
                data=CONFIG_PATH,
                epochs=TRAINING_CONFIG['epochs'],
                batch=batch,
                imgsz=TRAINING_CONFIG['imgsz'],
                patience=TRAINING_CONFIG['patience'],
                optimizer=TRAINING_CONFIG['optimizer'],
                lr0=TRAINING_CONFIG['lr0'],
                lrf=TRAINING_CONFIG['lrf'],
                warmup_epochs=TRAINING_CONFIG['warmup_epochs'],
                warmup_momentum=TRAINING_CONFIG['warmup_momentum'],
                weight_decay=TRAINING_CONFIG['weight_decay'],
                box=TRAINING_CONFIG['box'],
                cls=TRAINING_CONFIG['cls'],
                hsv_h=TRAINING_CONFIG['hsv_h'],
                hsv_s=TRAINING_CONFIG['hsv_s'],
                hsv_v=TRAINING_CONFIG['hsv_v'],
                degrees=TRAINING_CONFIG['degrees'],
                translate=TRAINING_CONFIG['translate'],
                scale=TRAINING_CONFIG['scale'],
                flipud=TRAINING_CONFIG['flipud'],
                fliplr=TRAINING_CONFIG['fliplr'],
                mosaic=TRAINING_CONFIG['mosaic'],
                mixup=TRAINING_CONFIG['mixup'],
                copy_paste=TRAINING_CONFIG['copy_paste'],
                project=RUNS_DIR,
                name=run_name,
                exist_ok=True,
                verbose=True,
                plots=True,
                save=True,
            )
        finally:
            allow_sleep()

    
    # Copy best weights
    best_weights = os.path.join(RUNS_DIR, run_name, "weights", "best.pt")
    if os.path.exists(best_weights):
        dest = os.path.join(WEIGHTS_DIR, "best.pt")
        shutil.copy2(best_weights, dest)
        print(f"\n[3/4] Best weights saved to: {dest}")
    
    last_weights = os.path.join(RUNS_DIR, run_name, "weights", "last.pt")
    if os.path.exists(last_weights):
        dest = os.path.join(WEIGHTS_DIR, "last.pt")
        shutil.copy2(last_weights, dest)
    
    print(f"[4/4] Training complete! Run: {run_name}")
    
    return model


# ===================== VALIDATION =====================

def validate_model(model_path=None):
    """Validate the trained model on the validation set."""
    from ultralytics import YOLO
    
    print("=" * 60)
    print("  Road AI - Model Validation")
    print("=" * 60)
    
    if model_path is None:
        model_path = os.path.join(WEIGHTS_DIR, "best.pt")
    
    if not os.path.exists(model_path):
        print(f"[ERROR] Model not found: {model_path}")
        print("Train a model first!")
        return None
    
    print(f"Loading model: {model_path}")
    model = YOLO(model_path)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = model.val(
        data=CONFIG_PATH,
        project=RUNS_DIR,
        name=f"val_{timestamp}",
        plots=True,
        verbose=True,
    )
    
    # Print key metrics
    print("\n" + "=" * 60)
    print("  VALIDATION RESULTS")
    print("=" * 60)
    
    metrics = {
        "mAP50": float(results.box.map50),
        "mAP50-95": float(results.box.map),
        "Precision": float(results.box.mp),
        "Recall": float(results.box.mr),
    }
    
    for metric_name, value in metrics.items():
        bar = "█" * int(value * 40)
        print(f"  {metric_name:>12}: {value:.4f}  {bar}")
    
    # Save metrics to JSON
    metrics_path = os.path.join(WEIGHTS_DIR, "metrics.json")
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"\n[OK] Metrics saved to: {metrics_path}")
    
    return results


# ===================== EXPORT =====================

def export_model(model_path=None):
    """Export model to ONNX format for deployment."""
    from ultralytics import YOLO
    
    print("=" * 60)
    print("  Road AI - Model Export (ONNX)")
    print("=" * 60)
    
    if model_path is None:
        model_path = os.path.join(WEIGHTS_DIR, "best.pt")
    
    if not os.path.exists(model_path):
        print(f"[ERROR] Model not found: {model_path}")
        return
    
    model = YOLO(model_path)
    
    # Export to ONNX
    print("Exporting to ONNX format...")
    onnx_path = model.export(
        format='onnx',
        imgsz=640,
        simplify=True,
        dynamic=False,
        opset=12,
    )
    
    # Copy to export directory
    if onnx_path and os.path.exists(onnx_path):
        dest = os.path.join(EXPORT_DIR, "road_defect_detector.onnx")
        shutil.copy2(onnx_path, dest)
        print(f"[OK] ONNX model exported to: {dest}")
        
        # Also export class names
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        meta = {
            'model_name': 'Road Defect Detector',
            'format': 'ONNX',
            'input_size': 640,
            'classes': config['names'],
            'exported_at': datetime.now().isoformat(),
        }
        meta_path = os.path.join(EXPORT_DIR, "model_metadata.json")
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)
        print(f"[OK] Metadata saved to: {meta_path}")


# ===================== TEST INFERENCE =====================

def test_inference(model_path=None, source=None):
    """Run inference on test images."""
    from ultralytics import YOLO
    
    print("=" * 60)
    print("  Road AI - Test Inference")
    print("=" * 60)
    
    if model_path is None:
        model_path = os.path.join(WEIGHTS_DIR, "best.pt")
    
    if not os.path.exists(model_path):
        print(f"[ERROR] Model not found: {model_path}")
        return
    
    if source is None:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        source = os.path.join(config['path'], 'images', 'test')
    
    if not os.path.exists(source):
        print(f"[ERROR] Test source not found: {source}")
        return
    
    model = YOLO(model_path)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = model.predict(
        source=source,
        conf=0.25,
        iou=0.45,
        save=True,
        save_txt=True,
        save_conf=True,
        project=RUNS_DIR,
        name=f"predict_{timestamp}",
        verbose=True,
    )
    
    # Collect summary
    total_detections = 0
    class_counts = {}
    
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            with open(CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f)
            cls_name = config['names'].get(cls_id, f"class_{cls_id}")
            
            if cls_name not in class_counts:
                class_counts[cls_name] = 0
            class_counts[cls_name] += 1
            total_detections += 1
    
    print(f"\n{'=' * 60}")
    print(f"  DETECTION SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Total detections: {total_detections}")
    for cls, count in sorted(class_counts.items(), key=lambda x: -x[1]):
        print(f"    {cls}: {count}")
    
    return results


# ===================== SEVERITY CLASSIFIER =====================

def classify_severity(area_ratio, defect_type):
    """
    Classify defect severity based on area and type.
    
    Severity rules (based on IRC/MORTH guidelines):
    - Low:    Small defects, cosmetic issues
    - Medium: Moderate defects requiring attention
    - High:   Severe defects requiring immediate repair
    
    area_ratio: ratio of defect bounding box area to image area
    """
    severity_thresholds = {
        "Pothole":              {"low": 0.005, "medium": 0.02},
        "Edge_Deterioration":   {"low": 0.01,  "medium": 0.05},
        "Alligator_Cracking":   {"low": 0.02,  "medium": 0.08},
        "Rutting":              {"low": 0.03,  "medium": 0.10},
        "Subsidence":           {"low": 0.01,  "medium": 0.04},
        "Cracking":             {"low": 0.01,  "medium": 0.05},
        "Bleeding":             {"low": 0.02,  "medium": 0.08},
        "Fretting":             {"low": 0.02,  "medium": 0.06},
        "Repaired_Pothole":     {"low": 0.01,  "medium": 0.03},
    }
    
    thresholds = severity_thresholds.get(defect_type, {"low": 0.01, "medium": 0.05})
    
    if area_ratio < thresholds["low"]:
        return "Low"
    elif area_ratio < thresholds["medium"]:
        return "Medium"
    else:
        return "High"


# ===================== SOR COST ESTIMATION =====================

# Schedule of Rates (SOR) - Cost per unit for road repairs
# Based on typical Indian SOR rates (in INR)
SOR_RATES = {
    "Pothole": {
        "Low":    {"rate_per_sqm": 350,  "description": "Pothole patching (cold mix)"},
        "Medium": {"rate_per_sqm": 550,  "description": "Pothole patching (hot mix)"},
        "High":   {"rate_per_sqm": 850,  "description": "Deep pothole repair with base course"},
    },
    "Edge_Deterioration": {
        "Low":    {"rate_per_sqm": 250,  "description": "Edge seal coating"},
        "Medium": {"rate_per_sqm": 450,  "description": "Edge patching"},
        "High":   {"rate_per_sqm": 750,  "description": "Edge reconstruction"},
    },
    "Alligator_Cracking": {
        "Low":    {"rate_per_sqm": 200,  "description": "Crack sealing"},
        "Medium": {"rate_per_sqm": 600,  "description": "Overlay patching"},
        "High":   {"rate_per_sqm": 1200, "description": "Full depth reclamation"},
    },
    "Rutting": {
        "Low":    {"rate_per_sqm": 300,  "description": "Surface leveling"},
        "Medium": {"rate_per_sqm": 700,  "description": "Milling and overlay"},
        "High":   {"rate_per_sqm": 1500, "description": "Full reconstruction"},
    },
    "Subsidence": {
        "Low":    {"rate_per_sqm": 400,  "description": "Surface patching"},
        "Medium": {"rate_per_sqm": 900,  "description": "Sub-base repair"},
        "High":   {"rate_per_sqm": 2000, "description": "Full depth reconstruction"},
    },
    "Cracking": {
        "Low":    {"rate_per_sqm": 150,  "description": "Crack sealing (filling)"},
        "Medium": {"rate_per_sqm": 400,  "description": "Crack routing and sealing"},
        "High":   {"rate_per_sqm": 800,  "description": "Full overlay"},
    },
    "Bleeding": {
        "Low":    {"rate_per_sqm": 100,  "description": "Sand blotting"},
        "Medium": {"rate_per_sqm": 300,  "description": "Micro-surfacing"},
        "High":   {"rate_per_sqm": 600,  "description": "Resurfacing"},
    },
    "Fretting": {
        "Low":    {"rate_per_sqm": 200,  "description": "Fog seal"},
        "Medium": {"rate_per_sqm": 450,  "description": "Surface dressing"},
        "High":   {"rate_per_sqm": 800,  "description": "Resurfacing"},
    },
    "Repaired_Pothole": {
        "Low":    {"rate_per_sqm": 100,  "description": "Monitoring only"},
        "Medium": {"rate_per_sqm": 350,  "description": "Re-patching"},
        "High":   {"rate_per_sqm": 650,  "description": "Redo repair"},
    },
}


def estimate_repair_cost(defect_type, severity, area_sqm=1.0):
    """Estimate repair cost based on SOR rates."""
    rates = SOR_RATES.get(defect_type, {}).get(severity, None)
    if rates is None:
        return {"cost": 0, "description": "No SOR rate available"}
    
    cost = rates["rate_per_sqm"] * area_sqm
    return {
        "cost": round(cost, 2),
        "rate_per_sqm": rates["rate_per_sqm"],
        "area_sqm": area_sqm,
        "description": rates["description"],
    }


# ===================== MAIN =====================

def main():
    parser = argparse.ArgumentParser(description="Road AI - Model Training Pipeline")
    parser.add_argument('--mode', type=str, default='full',
                        choices=['train', 'validate', 'export', 'test', 'full'],
                        help='Operation mode')
    parser.add_argument('--model', type=str, default=None,
                        help='Path to model weights')
    parser.add_argument('--source', type=str, default=None,
                        help='Source for test inference')
    parser.add_argument('--resume', action='store_true',
                        help='Resume training from last.pt')
    
    args = parser.parse_args()
    
    if args.mode == 'train' or args.mode == 'full':
        model = train_model(resume=args.resume, model_path=args.model)
    
    if args.mode == 'validate' or args.mode == 'full':
        validate_model(args.model)
    
    if args.mode == 'export' or args.mode == 'full':
        export_model(args.model)
    
    if args.mode == 'test' or args.mode == 'full':
        test_inference(args.model, args.source)


if __name__ == "__main__":
    main()
