"""Map source-image geometry into a confirmed coplanar 50 mm marker plane."""

import cv2
import numpy as np
from app.schemas.analysis import Box, Calibration
from app.services.marker_detector import MarkerDetectionResult


def calibrate(marker: MarkerDetectionResult, coplanar: bool) -> Calibration:
    reason = "Confirm that the printed 50 mm marker and label are in the same flat plane."
    if not marker.detected or not marker.bounding_box:
        reason = "Reference marker not detected."
    elif marker.marker_id != 0 or marker.dictionary != "ArUco 4x4_50":
        reason = "Use the standard ArUco 4x4_50 ID 0 marker."
    elif coplanar:
        points = np.array(marker.bounding_box, dtype=np.float32).reshape(4, 2)
        edges = np.linalg.norm(points - np.roll(points, -1, axis=0), axis=1)
        # Strong foreshortening makes extrapolated label measurements unreliable.
        if edges.min() < 40 or edges.max() / edges.min() > 1.3 or (marker.score or 0) < 0.9:
            reason = "Marker too small or oblique for reliable measurement. Retake face-on."
        else:
            target = np.array([[0, 0], [50, 0], [50, 50], [0, 50]], dtype=np.float32)
            matrix = cv2.getPerspectiveTransform(points, target)
            return Calibration(status="available", reason="Planar estimate, assumes actual printed marker measures 50 mm.",
                               pixels_per_mm=float(edges.mean() / 50), homography=matrix.tolist())
    return Calibration(status="unavailable", reason=reason)


def physical_height(box: Box | None, calibration: Calibration) -> float | None:
    """Estimate a text-line box height, not a legal glyph-height measurement."""
    if box is None or calibration.homography is None:
        return None
    corners = np.array([[[box.x0, box.y0], [box.x1, box.y0],
                         [box.x1, box.y1], [box.x0, box.y1]]], dtype=np.float32)
    mapped = cv2.perspectiveTransform(corners, np.array(calibration.homography))[0]
    height = float((np.linalg.norm(mapped[3] - mapped[0]) + np.linalg.norm(mapped[2] - mapped[1])) / 2)
    return round(height, 3) if np.isfinite(height) else None
