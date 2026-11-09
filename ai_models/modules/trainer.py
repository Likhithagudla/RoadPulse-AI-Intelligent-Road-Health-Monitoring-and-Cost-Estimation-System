"""
RoadPulse AI - Model Training Engine
Configurable, reproducible YOLOv8 training pipeline supporting GPU/CPU,
checkpoint saving, early stopping, resume capability, and metrics logging.
"""

import os
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from .config_loader import (
    AI_MODELS_DIR,
    WEIGHTS_DIR,
    RUNS_DIR,
    ensure_dataset_yaml_path,
    get_device,
    set_seed,
    patch_torch_load,
)
from .dataset_validator import DatasetValidator


class ModelTrainer:
    def __init__(
        self,
        base_model: str = "yolov8s-seg.pt",
        data_yaml: Optional[Path] = None,
        imgsz: int = 640,
        batch_size: int = 4,
        epochs: int = 50,
        lr0: float = 0.001,
        patience: int = 20,
        device: Optional[str] = None,
        seed: int = 42,
        output_dir: Optional[Path] = None,
    ):
        self.base_model = base_model
        self.data_yaml = Path(data_yaml) if data_yaml else ensure_dataset_yaml_path()
        self.imgsz = imgsz
        self.batch_size = batch_size
        self.epochs = epochs
        self.lr0 = lr0
        self.patience = patience
        self.seed = seed
        self.device = get_device(device)
        self.output_dir = Path(output_dir) if output_dir else RUNS_DIR
        self.weights_dir = WEIGHTS_DIR

        self.weights_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def train(self, resume: bool = False, checkpoint_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes YOLOv8 model training with deterministic settings and checkpoint management.
        """
        patch_torch_load()
        set_seed(self.seed)

        # 1. Validate dataset integrity before training
        print(f"[INFO] Validating dataset at: {self.data_yaml}")
        validator = DatasetValidator()
        v_report = validator.validate()
        if not v_report["is_valid"]:
            raise RuntimeError(f"Dataset validation failed: {v_report['errors']}")
        if v_report["data_leakage_detected"]:
            raise RuntimeError("Data leakage detected between splits! Training aborted.")

        print(f"[OK] Dataset verified: {v_report['total_images']} images across train/val/test.")
        print(f"[OK] Training device: {self.device} (Reproducible seed: {self.seed})")

        from ultralytics import YOLO

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_name = f"roadpulse_{timestamp}"

        if resume:
            resume_target = checkpoint_path or str(self.weights_dir / "last.pt")
            if not os.path.exists(resume_target):
                raise FileNotFoundError(f"Cannot resume: Checkpoint not found at {resume_target}")
            print(f"[INFO] Resuming training from checkpoint: {resume_target}")
            model = YOLO(resume_target)
            results = model.train(
                resume=True,
                device=self.device,
                workers=2,
            )
        else:
            model_source = checkpoint_path or self.base_model
            print(f"[INFO] Initializing model: {model_source}")
            model = YOLO(model_source)
            results = model.train(
                data=str(self.data_yaml),
                epochs=self.epochs,
                batch=self.batch_size,
                imgsz=self.imgsz,
                patience=self.patience,
                lr0=self.lr0,
                optimizer="AdamW",
                device=self.device,
                seed=self.seed,
                project=str(self.output_dir),
                name=run_name,
                exist_ok=True,
                save=True,
                save_period=5,
                val=True,
                plots=True,
                verbose=True,
            )

        # Copy best.pt to canonical weights directory
        run_best = Path(results.save_dir) / "weights" / "best.pt"
        run_last = Path(results.save_dir) / "weights" / "last.pt"
        
        saved_best = self.weights_dir / "best.pt"
        saved_last = self.weights_dir / "last.pt"

        if run_best.exists():
            import shutil
            shutil.copy2(run_best, saved_best)
            print(f"[OK] Checkpoint saved: {saved_best}")
        if run_last.exists():
            import shutil
            shutil.copy2(run_last, saved_last)
            print(f"[OK] Last checkpoint saved: {saved_last}")

        summary = {
            "run_name": run_name,
            "save_dir": str(results.save_dir),
            "device": self.device,
            "seed": self.seed,
            "epochs_trained": self.epochs,
            "best_weights": str(saved_best),
            "timestamp": timestamp,
        }

        # Export training summary JSON
        summary_path = Path(results.save_dir) / "training_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return summary
