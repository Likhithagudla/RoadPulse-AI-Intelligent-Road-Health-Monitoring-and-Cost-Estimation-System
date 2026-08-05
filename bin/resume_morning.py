import os
import ctypes
from ultralytics import YOLO

def prevent_sleep():
    """Prevents Windows from entering sleep mode while this Python script runs."""
    try:
        # ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x00000001)
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        print("[INFO] Windows sleep mode has been disabled for the duration of the training.")
    except Exception as e:
        print(f"[WARNING] Could not disable sleep mode: {e}")

def allow_sleep():
    """Restores Windows sleep mode restrictions."""
    try:
        # ES_CONTINUOUS (0x80000000)
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
    except:
        pass

def main():
    prevent_sleep()
    try:
        print("Resuming morning training process from: road_defect_20260225_101404...")
        pt_path = "runs/road_defect_20260225_101404/weights/last.pt"
        if not os.path.exists(pt_path):
            print("Could not find the weights from the morning training at:", pt_path)
            return

        model = YOLO(pt_path)
        model.train(resume=True)
    finally:
        allow_sleep()

if __name__ == "__main__":
    main()
