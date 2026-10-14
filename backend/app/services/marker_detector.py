"""
Reference-marker detection service.

Detects ArUco markers (OpenCV) in a package image.
Returns bounding-box coordinates, pixel dimensions, and a quality score.

This module provides marker *detection* only.
Pixel-to-physical-scale calibration is a later milestone (Week 4).
"""

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


# Default marker dictionary — ArUco 4×4 (50 markers).
# Can be changed if a different dictionary is printed.
_DEFAULT_DICT = cv2.aruco.DICT_4X4_50


@dataclass
class MarkerDetectionResult:
    """Result of attempting to detect a reference marker in an image."""

    detected: bool
    bounding_box: Optional[list[float]] = None   # [x1,y1, x2,y2, x3,y3, x4,y4]
    pixel_width: Optional[float] = None
    pixel_height: Optional[float] = None
    score: Optional[float] = None                 # 0.0–1.0 quality heuristic
    message: str = ""


def detect_marker(
    image_bytes: bytes,
    *,
    marker_dict: int = _DEFAULT_DICT,
    expected_marker_mm: float = 50.0,             # configurable physical size
) -> MarkerDetectionResult:
    """
    Detect an ArUco reference marker in the given image bytes.

    Parameters
    ----------
    image_bytes : bytes
        Raw bytes of a JPEG/PNG image.
    marker_dict : int
        OpenCV ArUco dictionary constant.
    expected_marker_mm : float
        Physical side-length of the printed marker in millimetres.
        Stored for future calibration use; not used in this step.

    Returns
    -------
    MarkerDetectionResult
    """
    # Decode image
    np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if image is None:
        return MarkerDetectionResult(
            detected=False,
            message="Could not decode image.",
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # ArUco detection
    aruco_dict = cv2.aruco.getPredefinedDictionary(marker_dict)
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, params)

    corners, ids, _rejected = detector.detectMarkers(gray)

    if ids is None or len(ids) == 0:
        return MarkerDetectionResult(
            detected=False,
            message="Reference marker not detected — calibration unavailable.",
        )

    # Use the first detected marker
    marker_corners = corners[0].reshape(4, 2)  # shape (4, 2) — four corner points

    # Flatten to [x1,y1, x2,y2, x3,y3, x4,y4]
    flat_box = marker_corners.flatten().tolist()

    # Pixel width  = average of top-edge and bottom-edge lengths
    top_edge = float(np.linalg.norm(marker_corners[1] - marker_corners[0]))
    bottom_edge = float(np.linalg.norm(marker_corners[2] - marker_corners[3]))
    px_width = (top_edge + bottom_edge) / 2.0

    # Pixel height = average of left-edge and right-edge lengths
    left_edge = float(np.linalg.norm(marker_corners[3] - marker_corners[0]))
    right_edge = float(np.linalg.norm(marker_corners[2] - marker_corners[1]))
    px_height = (left_edge + right_edge) / 2.0

    # Quality heuristic: ratio of detected area to a perfect square
    # (a severely perspective-distorted marker will score lower)
    detected_area = float(cv2.contourArea(marker_corners.astype(np.float32)))
    ideal_area = px_width * px_height
    score = round(min(detected_area / ideal_area, 1.0), 3) if ideal_area > 0 else 0.0

    flat_ids = np.asarray(ids).flatten()
    marker_id = int(flat_ids[0])

    return MarkerDetectionResult(
        detected=True,
        bounding_box=[round(v, 1) for v in flat_box],
        pixel_width=round(px_width, 1),
        pixel_height=round(px_height, 1),
        score=score,
        message=f"Marker detected (ID {marker_id}).",
    )
