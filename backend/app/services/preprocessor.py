"""
Image Preprocessing Pipeline for Nirikshak-LM.

Reproducible, evidence-preserving image enhancement pipeline:
1. Input Validation: Safely detects corrupt/invalid images without crashing.
2. Original Evidence Preservation: Never mutates raw source bytes.
3. Edge-Preserving Denoising: Bilateral filtering to smooth texture noise while preserving sharp character contours.
4. Local Contrast Enhancement: Contrast-Limited Adaptive Histogram Equalization (CLAHE) for legible text separation.
5. Planar Perspective Rectification:
   - ONLY applied when an unambiguous, convex 4-corner package quadrangle is reliably identified.
   - Otherwise safely skips rectification to strictly prevent geometric distortion of characters or physical ratios.
6. Execution Metadata: Tracks algorithm version, steps applied, and SHA-256 hashes.
"""

from typing import Dict, Any, Tuple, Optional, Union, List
import hashlib
from datetime import datetime, timezone
import cv2
import numpy as np

ALGORITHM_VERSION = "v1.0.0-nir-prep"


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Order coordinates consistently:
    [0]: Top-Left, [1]: Top-Right, [2]: Bottom-Right, [3]: Bottom-Left.
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # Top-left has smallest sum (x + y)
    rect[2] = pts[np.argmax(s)]  # Bottom-right has largest sum (x + y)

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # Top-right has smallest difference (y - x)
    rect[3] = pts[np.argmax(diff)]  # Bottom-left has largest difference (y - x)

    return rect


def calculate_interior_angles(pts: np.ndarray) -> List[float]:
    """Calculate the 4 internal angles of an ordered quadrangle in degrees."""
    angles = []
    for i in range(4):
        prev_pt = pts[(i - 1) % 4]
        curr_pt = pts[i]
        next_pt = pts[(i + 1) % 4]

        v1 = prev_pt - curr_pt
        v2 = next_pt - curr_pt

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            angles.append(0.0)
            continue

        cosine = np.dot(v1, v2) / (norm1 * norm2)
        cosine = float(np.clip(cosine, -1.0, 1.0))
        angle = float(np.degrees(np.arccos(cosine)))
        angles.append(angle)

    return angles


def detect_package_quadrilateral(
    image: np.ndarray,
) -> Tuple[Optional[np.ndarray], str]:
    """
    Attempt to identify an unambiguous, convex quadrilateral corresponding to the packaging face.
    Returns (ordered_pts, reason_str).
    If no valid quadrangle passes all validation checks, returns (None, explanation).
    """
    h, w = image.shape[:2]
    total_area = float(h * w)

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Blur gently to remove minor textures
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Edge detection with automatic Otsu-based thresholds
    high_thresh, _ = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    low_thresh = 0.5 * high_thresh
    edges = cv2.Canny(blurred, low_thresh, high_thresh)

    # Morphological closing to seal boundary gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Find external contours
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, "No external contours detected in image."

    # Sort contours by area descending
    sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for cnt in sorted_contours[:5]:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.025 * peri, True)

        # Check 1: Must have exactly 4 vertices
        if len(approx) != 4:
            continue

        # Check 2: Must be convex
        if not cv2.isContourConvex(approx):
            continue

        # Check 3: Area must be substantial (12% to 95% of frame)
        area = float(cv2.contourArea(approx))
        area_ratio = area / total_area
        if area_ratio < 0.12:
            continue
        if area_ratio > 0.96:
            continue

        pts = approx.reshape(4, 2).astype("float32")
        ordered = order_points(pts)

        # Check 4: Aspect ratio between 0.25 and 4.0
        tl, tr, br, bl = ordered
        w_top = np.linalg.norm(tr - tl)
        w_bot = np.linalg.norm(br - bl)
        h_left = np.linalg.norm(bl - tl)
        h_right = np.linalg.norm(br - tr)

        max_w = max(w_top, w_bot)
        max_h = max(h_left, h_right)
        if max_w == 0 or max_h == 0:
            continue

        aspect_ratio = max_w / max_h
        if aspect_ratio < 0.25 or aspect_ratio > 4.0:
            continue

        # Check 5: Internal angles must be approximately rectangular (55° - 125°)
        angles = calculate_interior_angles(ordered)
        if any(a < 55.0 or a > 125.0 for a in angles):
            continue

        return ordered, "Valid convex package quadrilateral identified."

    return None, "No unambiguous planar package quadrangle detected; skipped perspective rectification to avoid text distortion."


def rectify_perspective(
    image: np.ndarray,
    ordered_pts: np.ndarray,
) -> np.ndarray:
    """
    Warp quadrilateral to frontal canonical rectangular view.
    """
    tl, tr, br, bl = ordered_pts

    # Calculate optimal target dimensions
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = int(max(width_a, width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = int(max(height_a, height_b))

    dst = np.array(
        [
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1],
        ],
        dtype="float32",
    )

    m = cv2.getPerspectiveTransform(ordered_pts, dst)
    warped = cv2.warpPerspective(image, m, (max_width, max_height))
    return warped


def preprocess_package_image(
    image_input: Union[bytes, np.ndarray],
    enable_perspective_correction: bool = True,
) -> Dict[str, Any]:
    """
    Execute full preprocessing pipeline on input image.
    Preserves original evidence; creates a separate enhanced processed image.
    """
    # 1. Input Validation
    if isinstance(image_input, bytes):
        if len(image_input) == 0:
            return {
                "success": False,
                "error": "Empty image byte array provided.",
                "algorithm_version": ALGORITHM_VERSION,
            }
        raw_bytes = image_input
        nparr = np.frombuffer(image_input, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {
                "success": False,
                "error": "Corrupted image data; unable to decode JPEG/PNG.",
                "algorithm_version": ALGORITHM_VERSION,
            }
    elif isinstance(image_input, np.ndarray):
        img = image_input.copy()
        _, enc = cv2.imencode(".jpg", img)
        raw_bytes = enc.tobytes()
    else:
        return {
            "success": False,
            "error": f"Invalid input type: {type(image_input)}",
            "algorithm_version": ALGORITHM_VERSION,
        }

    orig_h, orig_w = img.shape[:2]
    steps_applied = ["input_validation"]

    # 2. Planar Perspective Rectification (Safe / Conditional)
    perspective_rectified = False
    perspective_reason = "Perspective rectification disabled by configuration."
    working_image = img

    if enable_perspective_correction:
        quad_pts, reason = detect_package_quadrilateral(img)
        perspective_reason = reason
        if quad_pts is not None:
            working_image = rectify_perspective(img, quad_pts)
            perspective_rectified = True
            steps_applied.append("perspective_rectification")

    # 3. Grayscale Conversion
    if len(working_image.shape) == 3:
        gray = cv2.cvtColor(working_image, cv2.COLOR_BGR2GRAY)
    else:
        gray = working_image
    steps_applied.append("grayscale_conversion")

    # 4. Edge-Preserving Denoising (Bilateral Filter)
    # Smooths high-frequency sensor noise without blurring text character contours
    denoised = cv2.bilateralFilter(gray, d=5, sigmaColor=40, sigmaSpace=40)
    steps_applied.append("bilateral_denoising")

    # 5. Local Contrast Enhancement (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    steps_applied.append("clahe_contrast_enhancement")

    # Encode processed result as clean JPEG
    # We output a 3-channel version so downstream viewers and web interfaces handle it uniformly
    processed_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    success, processed_bytes = cv2.imencode(".jpg", processed_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    if not success:
        return {
            "success": False,
            "error": "Failed to encode preprocessed image to JPEG.",
            "algorithm_version": ALGORITHM_VERSION,
        }

    processed_bytes = processed_bytes.tobytes()
    processed_h, processed_w = processed_bgr.shape[:2]
    processed_hash = hashlib.sha256(processed_bytes).hexdigest()
    raw_hash = hashlib.sha256(raw_bytes).hexdigest()

    return {
        "success": True,
        "algorithm_version": ALGORITHM_VERSION,
        "steps_applied": steps_applied,
        "perspective_rectified": perspective_rectified,
        "perspective_reason": perspective_reason,
        "original_dimensions": [orig_w, orig_h],
        "processed_dimensions": [processed_w, processed_h],
        "raw_file_hash": raw_hash,
        "processed_file_hash": processed_hash,
        "processed_bytes": processed_bytes,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
