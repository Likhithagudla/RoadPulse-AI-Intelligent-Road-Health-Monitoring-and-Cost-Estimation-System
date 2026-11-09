"""
RoadPulse AI - Visualizer
Renders high-visibility bounding boxes, polygon masks, confidence scores,
physical severity, and SOR repair cost tags onto images and video frames.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


# Color scheme (BGR format for OpenCV)
CLASS_COLORS = {
    "Pothole": (0, 0, 230),            # Vibrant Red
    "Traffic_Sign": (230, 180, 0),      # Cyan/Blue
    "Edge_Deterioration": (0, 140, 255),# Orange
    "Alligator_Cracking": (0, 69, 255), # Red-Orange
    "Rutting": (180, 0, 180),           # Purple
    "Subsidence": (255, 0, 128),        # Magenta
    "Cracking": (0, 165, 255),          # Amber
    "Default": (0, 255, 0),             # Green
}


class ResultVisualizer:
    @staticmethod
    def draw_detections(
        image: np.ndarray,
        detections: List[Dict[str, Any]],
        show_masks: bool = True,
        show_cost: bool = True,
        show_severity: bool = True,
        line_thickness: int = 2,
    ) -> np.ndarray:
        """
        Draws bounding boxes, polygons, and labels onto an OpenCV BGR image.
        """
        canvas = image.copy()
        overlay = canvas.copy()

        for det in detections:
            cls_name = det.get("class_name", "Unknown")
            conf = det.get("confidence", 0.0)
            severity = det.get("severity", "")
            bbox = det.get("bbox", {})
            polygon = det.get("polygon")
            repair_info = det.get("repair_cost", {})
            cost = repair_info.get("cost", 0) if isinstance(repair_info, dict) else 0

            color = CLASS_COLORS.get(cls_name, CLASS_COLORS["Default"])

            # 1. Draw segmentation polygon if present
            if show_masks and polygon and len(polygon) >= 3:
                pts = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
                cv2.fillPoly(overlay, [pts], color)
                cv2.polylines(canvas, [pts], isClosed=True, color=color, thickness=line_thickness)

            # 2. Draw bounding box
            if bbox and "x1" in bbox:
                x1, y1 = int(bbox["x1"]), int(bbox["y1"])
                x2, y2 = int(bbox["x2"]), int(bbox["y2"])
                cv2.rectangle(canvas, (x1, y1), (x2, y2), color, line_thickness)

                # Prepare label text
                label = f"{cls_name} {conf:.2f}"
                if show_severity and severity and severity not in ("N/A", "Unknown"):
                    label += f" [{severity}]"
                if show_cost and cost > 0:
                    label += f" | Rs.{int(cost)}"

                # Draw label background banner
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.5
                thickness = 1
                (w, h), _ = cv2.getTextSize(label, font, font_scale, thickness)

                banner_y1 = max(0, y1 - h - 6)
                banner_y2 = y1
                cv2.rectangle(canvas, (x1, banner_y1), (x1 + w + 8, banner_y2), color, -1)
                cv2.putText(
                    canvas,
                    label,
                    (x1 + 4, y1 - 4),
                    font,
                    font_scale,
                    (255, 255, 255),
                    thickness,
                    lineType=cv2.LINE_AA,
                )

        # Blend polygon overlay with original image (alpha transparency 0.3)
        if show_masks:
            cv2.addWeighted(overlay, 0.3, canvas, 0.7, 0, canvas)

        return canvas

    @staticmethod
    def save_annotated(
        image: np.ndarray,
        output_path: Path,
        detections: List[Dict[str, Any]],
        show_masks: bool = True,
        show_cost: bool = True,
        show_severity: bool = True,
    ) -> Path:
        """Saves annotated image directly to disk."""
        annotated = ResultVisualizer.draw_detections(
            image,
            detections,
            show_masks=show_masks,
            show_cost=show_cost,
            show_severity=show_severity,
        )
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_p), annotated)
        return out_p
