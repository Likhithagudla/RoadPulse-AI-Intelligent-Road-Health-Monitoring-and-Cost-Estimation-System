"""
RoadPulse AI - Model Training CLI Entrypoint
Usage:
    python train.py --epochs 50 --batch 4 --device cpu
    python train.py --resume
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules.trainer import ModelTrainer
from modules.config_loader import ensure_dataset_yaml_path


def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8 for RoadPulse AI")
    parser.add_argument("--model", type=str, default="yolov8s-seg.pt", help="Base model weights or architecture")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=4, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution")
    parser.add_argument("--lr", type=float, default=0.001, help="Initial learning rate")
    parser.add_argument("--patience", type=int, default=20, help="Early stopping patience")
    parser.add_argument("--device", type=str, default=None, help="Device ('cpu', 'cuda', 'auto')")
    parser.add_argument("--seed", type=int, default=42, help="Reproducible random seed")
    parser.add_argument("--resume", action="store_true", help="Resume training from last.pt")
    parser.add_argument("--checkpoint", type=str, default=None, help="Specific checkpoint path")

    args = parser.parse_args()

    # Verify and update dataset yaml path
    ensure_dataset_yaml_path()

    trainer = ModelTrainer(
        base_model=args.model,
        imgsz=args.imgsz,
        batch_size=args.batch,
        epochs=args.epochs,
        lr0=args.lr,
        patience=args.patience,
        device=args.device,
        seed=args.seed,
    )

    summary = trainer.train(resume=args.resume, checkpoint_path=args.checkpoint)
    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE")
    print("=" * 60)
    print(f"Run output: {summary['save_dir']}")
    print(f"Best weights: {summary['best_weights']}")


if __name__ == "__main__":
    main()
