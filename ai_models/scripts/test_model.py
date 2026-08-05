"""
RoadPulse AI - Step 5: Test the Trained Model
Runs the model on test images and saves results with bounding boxes.
"""
import sys
import os
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def main():
    print("=" * 60)
    print("  RoadPulse AI - Model Testing (Step 5)")
    print("=" * 60)
    print()

    # ── Paths ──────────────────────────────────────────────
    WEIGHTS = Path("D:/Road_AI_Project/ai_models/weights/best.pt")
    TEST_IMAGES = Path("D:/Road_AI_Project/ai_models/dataset/unified/test/images")
    OUTPUT_DIR = Path("D:/Road_AI_Project/ai_models/test_results")

    # Check model exists
    if not WEIGHTS.exists():
        print("ERROR: best.pt not found! Train the model first (Step 4).")
        sys.exit(1)

    # Check test images
    test_imgs = sorted(TEST_IMAGES.glob("*.jpg")) + sorted(TEST_IMAGES.glob("*.png"))
    if not test_imgs:
        print("ERROR: No test images found!")
        sys.exit(1)

    print(f"  Model: {WEIGHTS}")
    print(f"  Test images: {len(test_imgs)} images")
    print()

    # ── Load Model ─────────────────────────────────────────
    print("[1/3] Loading trained model...")
    from ultralytics import YOLO
    model = YOLO(str(WEIGHTS))
    print("  Model loaded successfully!")
    print()

    # ── Run Inference ──────────────────────────────────────
    print(f"[2/3] Running detection on {len(test_imgs)} test images...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = model.predict(
        source=str(TEST_IMAGES),
        save=True,
        save_txt=True,
        save_conf=True,
        project=str(OUTPUT_DIR),
        name="detections",
        exist_ok=True,
        conf=0.25,           # Confidence threshold (25%)
        iou=0.45,            # NMS IoU threshold
        imgsz=416,
        device="cpu",
        verbose=False,
    )

    # ── Analyze Results ────────────────────────────────────
    print()
    print("[3/3] Analyzing detection results...")
    print()

    total_detections = 0
    images_with_detections = 0
    confidence_scores = []
    severity_counts = {"High": 0, "Medium": 0, "Low": 0}

    print(f"  {'Image':<25} {'Detections':<12} {'Avg Conf':<10} {'Details'}")
    print(f"  {'-'*25} {'-'*12} {'-'*10} {'-'*30}")

    for r in results:
        img_name = Path(r.path).name
        n_detections = len(r.boxes)
        total_detections += n_detections

        if n_detections > 0:
            images_with_detections += 1
            confs = r.boxes.conf.tolist()
            avg_conf = sum(confs) / len(confs)
            confidence_scores.extend(confs)

            # Classify severity based on detection count and confidence
            details = []
            for conf in confs:
                if conf > 0.7:
                    severity_counts["High"] += 1
                    details.append(f"HIGH({conf:.0%})")
                elif conf > 0.4:
                    severity_counts["Medium"] += 1
                    details.append(f"MED({conf:.0%})")
                else:
                    severity_counts["Low"] += 1
                    details.append(f"LOW({conf:.0%})")

            detail_str = ", ".join(details[:4])
            if len(details) > 4:
                detail_str += f" +{len(details)-4} more"

            print(f"  {img_name:<25} {n_detections:<12} {avg_conf:<10.1%} {detail_str}")
        else:
            print(f"  {img_name:<25} {'0':<12} {'N/A':<10} (no potholes detected)")

    # ── Summary ────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"  Total test images:         {len(test_imgs)}")
    print(f"  Images with detections:    {images_with_detections}")
    print(f"  Total potholes found:      {total_detections}")

    if confidence_scores:
        avg_all = sum(confidence_scores) / len(confidence_scores)
        max_conf = max(confidence_scores)
        min_conf = min(confidence_scores)
        print(f"  Average confidence:        {avg_all:.1%}")
        print(f"  Highest confidence:        {max_conf:.1%}")
        print(f"  Lowest confidence:         {min_conf:.1%}")

    print()
    print(f"  Severity breakdown:")
    print(f"    HIGH (>70% conf):   {severity_counts['High']} detections")
    print(f"    MEDIUM (40-70%):    {severity_counts['Medium']} detections")
    print(f"    LOW (<40%):         {severity_counts['Low']} detections")

    # Detection rate
    detection_rate = images_with_detections / len(test_imgs) * 100
    print()
    print(f"  Detection rate: {detection_rate:.0f}% of images had potholes")

    # ── Generate HTML Report ───────────────────────────────
    print()
    print("  Generating visual report...")
    generate_html_report(OUTPUT_DIR, results)

    print()
    print(f"  Output saved to: {OUTPUT_DIR / 'detections'}")
    print(f"  Visual report:   {OUTPUT_DIR / 'report.html'}")
    print()
    print("  Open the report.html file in your browser to see all")
    print("  detected potholes with bounding boxes drawn on them!")
    print("=" * 60)


def generate_html_report(output_dir, results):
    """Generate an HTML report showing all test results."""
    detection_dir = output_dir / "detections"

    # Get all result images
    result_images = sorted(detection_dir.glob("*.jpg")) + sorted(detection_dir.glob("*.png"))

    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RoadPulse AI - Detection Results</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: #0a0e1a;
            color: #e0e6f0;
            padding: 2rem;
        }
        h1 {
            text-align: center;
            font-size: 2rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #00e5ff, #7c4dff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            text-align: center;
            color: #8892b0;
            margin-bottom: 2rem;
        }
        .stats {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 1.2rem 2rem;
            text-align: center;
            min-width: 160px;
        }
        .stat-card .value {
            font-size: 2rem;
            font-weight: 700;
            color: #00e5ff;
        }
        .stat-card .label {
            font-size: 0.85rem;
            color: #8892b0;
            margin-top: 0.3rem;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 1.5rem;
        }
        .card {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            overflow: hidden;
            transition: transform 0.2s;
        }
        .card:hover { transform: translateY(-4px); border-color: #00e5ff44; }
        .card img {
            width: 100%;
            height: auto;
            display: block;
        }
        .card-info {
            padding: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .card-name { font-weight: 600; }
        .badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .badge.found { background: rgba(0,229,255,0.15); color: #00e5ff; }
        .badge.none { background: rgba(255,255,255,0.05); color: #5a6380; }
    </style>
</head>
<body>
    <h1>RoadPulse AI - Detection Results</h1>
    <p class="subtitle">YOLOv8 Pothole Detection Test Results</p>
"""

    # Compute stats
    total_imgs = len(results)
    total_dets = sum(len(r.boxes) for r in results)
    imgs_with_det = sum(1 for r in results if len(r.boxes) > 0)
    all_confs = []
    for r in results:
        all_confs.extend(r.boxes.conf.tolist())
    avg_conf = sum(all_confs) / len(all_confs) if all_confs else 0

    html += f"""
    <div class="stats">
        <div class="stat-card"><div class="value">{total_imgs}</div><div class="label">Test Images</div></div>
        <div class="stat-card"><div class="value">{total_dets}</div><div class="label">Potholes Found</div></div>
        <div class="stat-card"><div class="value">{imgs_with_det}</div><div class="label">Images with Detections</div></div>
        <div class="stat-card"><div class="value">{avg_conf:.0%}</div><div class="label">Avg Confidence</div></div>
    </div>
    <div class="grid">
"""

    for img_path in result_images:
        name = img_path.name
        # Find matching result
        n_det = 0
        for r in results:
            if Path(r.path).name == name:
                n_det = len(r.boxes)
                break

        badge_class = "found" if n_det > 0 else "none"
        badge_text = f"{n_det} pothole{'s' if n_det != 1 else ''}" if n_det > 0 else "No defects"

        # Use relative path for the image
        rel_path = f"detections/{name}"

        html += f"""
        <div class="card">
            <img src="{rel_path}" alt="{name}" loading="lazy">
            <div class="card-info">
                <span class="card-name">{name}</span>
                <span class="badge {badge_class}">{badge_text}</span>
            </div>
        </div>
"""

    html += """
    </div>
</body>
</html>"""

    report_path = output_dir / "report.html"
    with open(report_path, 'w') as f:
        f.write(html)

    print(f"  Report saved to: {report_path}")


if __name__ == "__main__":
    main()
