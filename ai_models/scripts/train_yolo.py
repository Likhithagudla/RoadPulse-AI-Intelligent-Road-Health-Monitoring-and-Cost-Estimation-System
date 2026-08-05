"""
RoadPulse AI - Step 4: Train YOLOv8 Model
Trains a pothole detection model on the prepared dataset.
"""
import sys
import os
from pathlib import Path
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

# Force UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("=" * 60)
    print("  RoadPulse AI - YOLOv8 Model Training (Step 4)")
    print("=" * 60)
    print()

    # ── Paths ──────────────────────────────────────────────
    DATA_YAML = "D:/Road_AI_Project/ai_models/dataset/unified/data.yaml"
    PROJECT_DIR = "D:/Road_AI_Project/ai_models/runs"
    WEIGHTS_DIR = "D:/Road_AI_Project/ai_models/weights"

    # Check dataset exists
    if not Path(DATA_YAML).exists():
        print("ERROR: data.yaml not found! Run prepare_data.py first.")
        sys.exit(1)

    print("[1/4] Loading YOLOv8...")
    from ultralytics import YOLO

    # ── Model Selection ────────────────────────────────────
    # yolov8n = Nano (fastest, good for CPU)
    # yolov8s = Small (better accuracy, slower)
    # yolov8m = Medium (best accuracy, slowest on CPU)
    MODEL_SIZE = "yolov8n.pt"  # Nano - best for CPU training

    print(f"  Using model: {MODEL_SIZE} (nano - optimized for CPU)")
    print(f"  Dataset: {DATA_YAML}")
    print()

    # ── Training Configuration ─────────────────────────────
    # These settings are tuned for CPU training with ~600 images
    EPOCHS = 50          # Number of training rounds (50 is good for first run)
    IMG_SIZE = 416       # Image size (smaller = faster training)
    BATCH_SIZE = 8       # Images per batch (8 is safe for CPU)
    PATIENCE = 15        # Stop early if no improvement for 15 epochs

    print("[2/4] Training configuration:")
    print(f"  Epochs:     {EPOCHS} (will stop early if no improvement)")
    print(f"  Image size: {IMG_SIZE}x{IMG_SIZE} pixels")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Patience:   {PATIENCE} epochs")
    print(f"  Device:     CPU")
    print()

    # ── Start Training ─────────────────────────────────────
    print("[3/4] Starting training... (this will take 1-2 hours on CPU)")
    print("  You will see progress after each epoch.")
    print("  The model saves automatically - you can stop anytime with Ctrl+C")
    print("-" * 60)

    model = YOLO(MODEL_SIZE)

    prevent_sleep()
    try:
        results = model.train(
            data=DATA_YAML,
            epochs=EPOCHS,
            imgsz=IMG_SIZE,
            batch=BATCH_SIZE,
            patience=PATIENCE,
            device="cpu",
            project=PROJECT_DIR,
            name="pothole_detector",
            exist_ok=True,

            # Performance settings for CPU
            workers=2,             # Data loading threads
            cache=True,            # Cache images in RAM (faster)

            # Augmentation (helps model learn better with small dataset)
            augment=True,
            hsv_h=0.015,           # Color variation
            hsv_s=0.5,
            hsv_v=0.3,
            degrees=10,            # Slight rotation
            translate=0.1,         # Shift image
            scale=0.3,             # Zoom in/out
            fliplr=0.5,            # Horizontal flip
            mosaic=1.0,            # Combine 4 images (great for small datasets)
            mixup=0.1,             # Blend images

            # Logging
            verbose=True,
            plots=True,            # Save training graphs
        )
    finally:
        allow_sleep()

    print("-" * 60)
    print()

    # ── Save Best Model ────────────────────────────────────
    print("[4/4] Saving trained model...")

    # Copy best weights to our weights directory
    Path(WEIGHTS_DIR).mkdir(parents=True, exist_ok=True)

    best_pt = Path(PROJECT_DIR) / "pothole_detector" / "weights" / "best.pt"
    last_pt = Path(PROJECT_DIR) / "pothole_detector" / "weights" / "last.pt"

    import shutil
    if best_pt.exists():
        dest = Path(WEIGHTS_DIR) / "best.pt"
        shutil.copy2(best_pt, dest)
        print(f"  Best model saved to: {dest}")
    if last_pt.exists():
        dest = Path(WEIGHTS_DIR) / "last.pt"
        shutil.copy2(last_pt, dest)
        print(f"  Last model saved to: {dest}")

    # ── Print Results ──────────────────────────────────────
    print()
    print("=" * 60)
    print("  TRAINING COMPLETE!")
    print("=" * 60)

    # Show metrics if available
    metrics_dir = Path(PROJECT_DIR) / "pothole_detector"
    if (metrics_dir / "results.csv").exists():
        import csv
        with open(metrics_dir / "results.csv") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                last = rows[-1]
                print(f"  Final epoch metrics:")
                for key in last:
                    key_clean = key.strip()
                    if any(m in key_clean for m in ['precision', 'recall', 'mAP', 'loss']):
                        try:
                            val = float(last[key])
                            print(f"    {key_clean}: {val:.4f}")
                        except ValueError:
                            pass

    print()
    print(f"  Model weights: {WEIGHTS_DIR}")
    print(f"  Training plots: {metrics_dir}")
    print()
    print("  Next: Run Step 5 to test the model on new images!")
    print("=" * 60)


if __name__ == "__main__":
    main()
