"""
RoadPulse AI - Model Evaluation CLI Entrypoint
Generates Precision, Recall, F1-Score, mAP@0.5, mAP@0.5:0.95, Confusion Matrix,
per-class performance, and False Positive / False Negative analysis on test data.

Usage:
    python evaluate.py --split test --conf 0.25
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules.evaluator import ModelEvaluator
from modules.config_loader import DEFAULT_WEIGHTS, ensure_dataset_yaml_path


def main():
    parser = argparse.ArgumentParser(description="Evaluate RoadPulse AI YOLOv8 model")
    parser.add_argument("--weights", type=str, default=str(DEFAULT_WEIGHTS), help="Path to best.pt")
    parser.add_argument("--split", type=str, default="test", choices=["test", "val", "train"], help="Split to evaluate")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.45, help="NMS IoU threshold")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution")
    parser.add_argument("--device", type=str, default=None, help="Device ('cpu', 'cuda', 'auto')")

    args = parser.parse_args()

    ensure_dataset_yaml_path()

    evaluator = ModelEvaluator(
        weights_path=Path(args.weights),
        device=args.device,
        imgsz=args.imgsz,
    )

    report = evaluator.evaluate(split=args.split, conf=args.conf, iou=args.iou)

    print("\n" + "=" * 65)
    print(f"  ROADPULSE AI - EVALUATION METRICS REPORT (Split: {args.split.upper()})")
    print("=" * 65)

    box = report["overall_metrics"]["box"]
    seg = report["overall_metrics"]["segmentation"]

    print("\n[OVERALL DETECTION PERFORMANCE]")
    print(f"  Precision:       {box['precision']:.4f}")
    print(f"  Recall:          {box['recall']:.4f}")
    print(f"  F1-Score:        {box['f1_score']:.4f}")
    print(f"  mAP @ 0.50:      {box['mAP50']:.4f}")
    print(f"  mAP @ 0.50:0.95: {box['mAP50_95']:.4f}")

    print("\n[OVERALL SEGMENTATION (MASK) PERFORMANCE]")
    print(f"  Precision:       {seg['precision']:.4f}")
    print(f"  Recall:          {seg['recall']:.4f}")
    print(f"  F1-Score:        {seg['f1_score']:.4f}")
    print(f"  mAP @ 0.50:      {seg['mAP50']:.4f}")
    print(f"  mAP @ 0.50:0.95: {seg['mAP50_95']:.4f}")

    print("\n[PER-CLASS BREAKDOWN]")
    print(f"  {'Class Name':<20} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'mAP@0.5':<12} {'mAP@0.5:0.95'}")
    print("  " + "-" * 75)
    for cname, cmetrics in report["per_class_metrics"].items():
        cb = cmetrics["box"]
        print(f"  {cname:<20} {cb['precision']:<12.4f} {cb['recall']:<12.4f} {cb['f1_score']:<12.4f} {cb['mAP50']:<12.4f} {cb['mAP50_95']:.4f}")

    ea = report["error_analysis"]
    print("\n[FALSE POSITIVE & FALSE NEGATIVE ERROR ANALYSIS]")
    print(f"  Total Test Images Scanned:       {ea['total_images_scanned']}")
    print(f"  Total Ground Truth Objects:      {ea['total_ground_truth_objects']}")
    print(f"  Total Predictions Made:          {ea['total_predictions']}")
    print(f"  False Positives (Spurious):      {ea['false_positives_count']}")
    print(f"  False Negatives (Missed):        {ea['false_negatives_count']}")
    
    if ea["false_positives_sample"]:
        print("\n  Sample False Positives:")
        for fp in ea["false_positives_sample"][:3]:
            print(f"    - Image: {fp['image']}, Predicted: {fp['predicted_class']} (conf={fp['confidence']}), Reason: {fp['reason']}")

    if ea["false_negatives_sample"]:
        print("\n  Sample False Negatives (Missed Defects):")
        for fn in ea["false_negatives_sample"][:3]:
            print(f"    - Image: {fn['image']}, GT Class: {fn['ground_truth_class']}, Reason: {fn['reason']}")

    print("\n" + "=" * 65 + "\n")


if __name__ == "__main__":
    main()
