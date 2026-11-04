"""
Reference-marker detection service.

Detects ArUco markers (OpenCV) in a package image.
Returns bounding-box coordinates, pixel dimensions, and a quality score.

This module provides marker *detection* and preliminary planar scale estimation.
Rigorous multi-view camera calibration is a later milestone (Week 4).
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List

import cv2
import numpy as np


# Default marker dictionary — ArUco 4×4 (50 markers).
_DEFAULT_DICT = cv2.aruco.DICT_4X4_50

# Supported dictionaries in order of preference
_SUPPORTED_DICTS: List[Tuple[str, int]] = [
    ("ArUco 4x4_50", cv2.aruco.DICT_4X4_50),
    ("ArUco 4x4_100", cv2.aruco.DICT_4X4_100),
    ("ArUco 4x4_250", cv2.aruco.DICT_4X4_250),
    ("ArUco 5x5_50", cv2.aruco.DICT_5X5_50),
    ("ArUco 6x6_50", cv2.aruco.DICT_6X6_50),
]


@dataclass
class MarkerDetectionResult:
    """Result of attempting to detect a reference marker in an image."""

    detected: bool
    marker_id: Optional[int] = None
    dictionary: Optional[str] = None
    bounding_box: Optional[list[float]] = None   # [x1,y1, x2,y2, x3,y3, x4,y4]
    pixel_width: Optional[float] = None
    pixel_height: Optional[float] = None
    score: Optional[float] = None                 # 0.0–1.0 planarity/distortion quality heuristic
    estimated_ppm: Optional[float] = None         # Preliminary pixels/mm assuming expected_marker_mm
    message: str = ""


def _get_detector_parameters() -> cv2.aruco.DetectorParameters:
    """Configure robust detector parameters for varied webcam lighting and distances."""
    params = cv2.aruco.DetectorParameters()
    params.adaptiveThreshWinSizeMin = 3
    params.adaptiveThreshWinSizeMax = 53
    params.adaptiveThreshWinSizeStep = 8
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    params.polygonalApproxAccuracyRate = 0.05
    return params


def detect_marker(
    image_bytes: bytes,
    *,
    marker_dict: int = _DEFAULT_DICT,
    expected_marker_mm: float = 50.0,             # standard 50 mm (5 cm) reference marker
) -> MarkerDetectionResult:
    """
    Detect an ArUco reference marker in the given image bytes.

    Uses a multi-pass approach:
    1. Standard detection using default dictionary and subpixel refinement.
    2. Adaptive CLAHE contrast enhancement for low-contrast/glare lighting.
    3. Multi-dictionary fallback if another standard ArUco dictionary was used.

    Parameters
    ----------
    image_bytes : bytes
        Raw bytes of a JPEG/PNG image.
    marker_dict : int
        OpenCV ArUco dictionary constant.
    expected_marker_mm : float
        Physical side-length of the printed marker in millimetres.

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
            message="Could not decode image format. Upload JPEG or PNG.",
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    params = _get_detector_parameters()

    # Pass 1: Primary dictionary on standard grayscale
    primary_dict = cv2.aruco.getPredefinedDictionary(marker_dict)
    detector = cv2.aruco.ArucoDetector(primary_dict, params)
    corners, ids, _ = detector.detectMarkers(gray)
    matched_dict_name = "ArUco 4x4_50"

    # Pass 2: Contrast-enhanced grayscale (CLAHE) for dim lighting or glare
    if ids is None or len(ids) == 0:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced_gray = clahe.apply(gray)
        corners, ids, _ = detector.detectMarkers(enhanced_gray)

    # Pass 3: Multi-dictionary fallback
    if ids is None or len(ids) == 0:
        for name, dict_id in _SUPPORTED_DICTS:
            if dict_id == marker_dict:
                continue
            alt_dict = cv2.aruco.getPredefinedDictionary(dict_id)
            alt_detector = cv2.aruco.ArucoDetector(alt_dict, params)
            c, i, _ = alt_detector.detectMarkers(gray)
            if i is not None and len(i) > 0:
                corners, ids = c, i
                matched_dict_name = name
                break

    if ids is None or len(ids) == 0:
        return MarkerDetectionResult(
            detected=False,
            message=(
                "Reference marker not detected — calibration unavailable. "
                "Ensure an ArUco 4x4_50 marker is clearly visible with its white border intact."
            ),
        )

    # Use the first detected marker
    marker_corners = corners[0].reshape(4, 2)  # shape (4, 2) — four corner points
    flat_box = marker_corners.flatten().tolist()

    # Pixel width  = average of top-edge and bottom-edge lengths
    top_edge = float(np.linalg.norm(marker_corners[1] - marker_corners[0]))
    bottom_edge = float(np.linalg.norm(marker_corners[2] - marker_corners[3]))
    px_width = (top_edge + bottom_edge) / 2.0

    # Pixel height = average of left-edge and right-edge lengths
    left_edge = float(np.linalg.norm(marker_corners[3] - marker_corners[0]))
    right_edge = float(np.linalg.norm(marker_corners[2] - marker_corners[1]))
    px_height = (left_edge + right_edge) / 2.0

    # Quality heuristic: ratio of detected contour area to an ideal planar square
    detected_area = float(cv2.contourArea(marker_corners.astype(np.float32)))
    ideal_area = px_width * px_height
    score = round(min(detected_area / ideal_area, 1.0), 3) if ideal_area > 0 else 0.0

    flat_ids = np.asarray(ids).flatten()
    marker_id = int(flat_ids[0])

    # Preliminary pixels-per-millimeter (preliminary scale estimate)
    estimated_ppm = round(px_width / expected_marker_mm, 3) if expected_marker_mm > 0 else None

    return MarkerDetectionResult(
        detected=True,
        marker_id=marker_id,
        dictionary=matched_dict_name,
        bounding_box=[round(v, 1) for v in flat_box],
        pixel_width=round(px_width, 1),
        pixel_height=round(px_height, 1),
        score=score,
        estimated_ppm=estimated_ppm,
        message=(
            f"Marker detected (ID {marker_id}, {matched_dict_name}). "
            f"Preliminary scale: {estimated_ppm} px/mm (assumes standard {expected_marker_mm:.1f} mm coplanar target)."
        ),
    )


def generate_reference_marker_image(
    marker_id: int = 0,
    marker_dict: int = _DEFAULT_DICT,
    size_px: int = 400,
    margin_px: int = 60,
) -> bytes:
    """
    Generate a printable high-contrast ArUco reference marker with white quiet zone and calibration ruler.

    Parameters
    ----------
    marker_id : int
        Marker ID within the dictionary (default 0).
    marker_dict : int
        ArUco dictionary (default DICT_4X4_50).
    size_px : int
        Pixel dimension of the black marker square.
    margin_px : int
        Pixel width of the surrounding white quiet zone.

    Returns
    -------
    bytes
        PNG image bytes.
    """
    aruco_dict = cv2.aruco.getPredefinedDictionary(marker_dict)
    marker_img = np.zeros((size_px, size_px), dtype=np.uint8)
    cv2.aruco.generateImageMarker(aruco_dict, marker_id, size_px, marker_img, 1)

    # White quiet zone margin + caption area
    padded = cv2.copyMakeBorder(
        marker_img, margin_px, margin_px + 45, margin_px, margin_px,
        cv2.BORDER_CONSTANT, value=255
    )
    color_img = cv2.cvtColor(padded, cv2.COLOR_GRAY2BGR)

    # Reference label and physical scale indicator
    caption = f"NIRIKSHAK-LM REFERENCE MARKER (50x50 mm | ArUco 4x4_50 ID: {marker_id})"
    sub_caption = "Print at 100% scale (50x50 mm). Keep white border intact."
    cv2.putText(
        color_img, caption, (margin_px - 20, color_img.shape[0] - 25),
        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (30, 30, 30), 1, cv2.LINE_AA
    )
    cv2.putText(
        color_img, sub_caption, (margin_px - 20, color_img.shape[0] - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.32, (100, 100, 100), 1, cv2.LINE_AA
    )

    success, png_bytes = cv2.imencode(".png", color_img)
    if not success:
        raise RuntimeError("Failed to encode reference marker image.")
    return png_bytes.tobytes()
