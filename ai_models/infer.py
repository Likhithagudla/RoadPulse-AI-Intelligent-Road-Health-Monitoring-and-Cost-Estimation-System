"""
RoadPulse AI - Inference CLI Entrypoint
Runs defect detection, perspective ground-plane area calculation,
IRC 82:2015 physical severity assessment, and 5-factor CPWD/MoRTH repair cost estimation.

Usage:
    python infer.py --source test_image.jpg --save-annotated
    python infer.py --source test_image.jpg --region Maharashtra --verbose
    python infer.py --source video.mp4 --conf 0.20
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules.detector import RoadDefectDetector
from modules.config_loader import DEFAULT_WEIGHTS


def main():
    parser = argparse.ArgumentParser(description="Inference CLI for RoadPulse AI")
    parser.add_argument("--source", type=str, required=True, help="Path to image, directory, or video file")
    parser.add_argument("--weights", type=str, default=str(DEFAULT_WEIGHTS), help="Path to weights file")
    parser.add_argument("--conf", type=float, default=0.15, help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.45, help="IoU threshold for NMS")
    parser.add_argument("--device", type=str, default=None, help="Device ('cpu', 'cuda', 'auto')")
    parser.add_argument("--region", type=str, default="Default", help="Region for SOR rates (e.g., Delhi, Maharashtra, Karnataka)")
    parser.add_argument("--output", type=str, default="runs/inference", help="Output directory")
    parser.add_argument("--save-annotated", action="store_true", help="Save visual bounding-box and mask overlay")
    parser.add_argument("--verbose", action="store_true", help="Print detailed 5-factor engineering cost breakdown")

    args = parser.parse_args()

    detector = RoadDefectDetector(
        weights_path=Path(args.weights),
        conf_threshold=args.conf,
        iou_threshold=args.iou,
        device=args.device,
    )

    src_path = Path(args.source)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not src_path.exists():
        print(f"[ERROR] Source not found: {src_path}")
        sys.exit(1)

    # Video inference
    if src_path.suffix.lower() in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
        print(f"[INFO] Running video detection on: {src_path} (Region: {args.region})")
        res = detector.process_video(src_path, conf_override=args.conf, region=args.region)
        print("\n" + "=" * 60)
        print("  ROAD DEFECT & COST ESTIMATION - VIDEO SUMMARY")
        print("=" * 60)
        print(f"Total Frames Processed: {res['frames_processed']} / {res['total_frames']}")
        print(f"Total Defects Found:    {res['total_defects']}")
        print(f"Region Index Applied:   {res['region_applied']}")
        print(f"Estimated Total Cost:   INR {res['estimated_total_cost']:,.2f}")
        print("\nDefect Breakdown:")
        for cname, count in res["defect_summary"].items():
            print(f"  {cname}: {count}")
        return

    # Image list
    if src_path.is_dir():
        image_files = [f for f in src_path.glob("*.*") if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    else:
        image_files = [src_path]

    print(f"[INFO] Running detection on {len(image_files)} image(s) [Region: {args.region}]...")

    for img_p in image_files:
        annot_target = output_dir / f"annotated_{img_p.name}" if args.save_annotated else None
        res = detector.detect_image(
            image_input=img_p,
            conf_override=args.conf,
            region=args.region,
            annotate=args.save_annotated,
            output_annotated_path=annot_target,
        )

        if not res.get("success"):
            print(f"  [FAIL] {img_p.name}: {res.get('error')}")
            continue

        dets = res["detections"]
        print(f"\nImage: {img_p.name} ({len(dets)} detected | Total Est. Cost: INR {res['estimated_total_cost']:,.2f})")
        for idx, d in enumerate(dets, 1):
            cost_info = d["repair_cost"]
            cost_str = f"INR {cost_info['cost']:,.2f}" if cost_info["cost"] > 0 else "N/A"
            geom = d.get("geometry_calibration", {})
            calib_str = "Calibrated" if geom.get("is_calibrated") else "Heuristic"

            print(f"  #{idx} [{d['class_name']}] Conf: {d['confidence']:.2f} | Severity: {d['severity']} | Area: {d['estimated_area_sqm']:.4f} m^2 ({calib_str}) | Cost: {cost_str}")

            if args.verbose and d.get("is_defect"):
                detail = d.get("detailed_cost_breakdown", {})
                bd = detail.get("cost_breakdown", {})
                ur = detail.get("uncertainty_range", {})
                print(f"      Treatment: {detail.get('repair_treatment')}")
                print(f"      Spec:      {detail.get('specification')}")
                print(f"      Breakdown: Mat: INR {bd.get('material_cost_inr', 0):.2f} | Lab: INR {bd.get('labour_cost_inr', 0):.2f} | Eqp: INR {bd.get('equipment_cost_inr', 0):.2f} | OH&P: INR {bd.get('contractor_overhead_profit_inr', 0):.2f} | Contingency: INR {bd.get('contingency_and_safety_inr', 0):.2f}")
                print(f"      Range:     INR {ur.get('min_cost_inr', 0):.2f} - INR {ur.get('max_cost_inr', 0):.2f} ({ur.get('confidence_band')})")
                print(f"      Status:    {detail.get('measurement_status')}")

        if annot_target and annot_target.exists():
            print(f"  -> Saved annotation: {annot_target}")


if __name__ == "__main__":
    main()
