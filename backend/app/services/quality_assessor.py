"""
Image Quality Assessment Service for Nirikshak-LM.

Evaluates package capture fidelity across:
1. Blur / Sharpness (Variance of Laplacian)
2. Lighting / Exposure (Mean luminance, shadow/highlight clipping ratios)
3. Contrast / Text Legibility (RMS contrast / intensity standard deviation)
4. Resolution / Framing Dimensions (Minimum width & height requirements)
5. Specular Glare / Clipped Hotspots (Localized high-intensity reflection)

Returns typed metrics, status determinations ('Pass', 'Warning', 'Retake Recommended'),
and actionable guidance for enforcement inspectors.

DISCLAIMER: This optical quality assessment evaluates capture clarity and readability.
It does NOT imply statutory compliance or non-compliance under the Legal Metrology Act, 2009.
"""

from typing import Dict, Any, List, Optional, Union
import cv2
import numpy as np


DEFAULT_THRESHOLDS = {
    # Sharpness (Variance of Laplacian)
    "blur_min_pass": 120.0,
    "blur_min_warn": 60.0,
    # Exposure (Mean pixel intensity 0-255)
    "underexposure_mean_min": 65.0,
    "underexposure_mean_fail": 45.0,
    "overexposure_mean_max": 195.0,
    "overexposure_mean_fail": 215.0,
    "dark_pixels_max_ratio": 0.35,  # Ratio of pixels < 25
    "bright_pixels_max_ratio": 0.25, # Ratio of pixels > 240
    # Contrast (Standard deviation of pixel intensities)
    "contrast_min_pass": 40.0,
    "contrast_min_warn": 25.0,
    # Dimensions (Pixels)
    "min_width": 640,
    "min_height": 480,
    "recommended_width": 1280,
    "recommended_height": 720,
    # Specular Glare (Percentage of pixels with intensity >= 252)
    "glare_max_warn_pct": 6.0,
    "glare_max_fail_pct": 15.0,
}

LEGAL_METROLOGY_QUALITY_DISCLAIMER = (
    "Image quality assessment evaluates optical clarity and capture fidelity. "
    "It does not constitute a determination of legal compliance under the "
    "Legal Metrology Act, 2009 or the Packaged Commodities Rules, 2011."
)


def evaluate_sharpness(
    gray: np.ndarray,
    thresholds: Dict[str, float] = DEFAULT_THRESHOLDS,
) -> Dict[str, Any]:
    """
    Evaluate image sharpness using Variance of Laplacian.
    Higher variance indicates sharp edges; low variance indicates motion or defocus blur.
    """
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = float(laplacian.var())
    score = float(min(100.0, max(0.0, (variance / 250.0) * 100.0)))

    if variance >= thresholds["blur_min_pass"]:
        status = "Pass"
        message = "Image is crisp with sharp edge definition."
    elif variance >= thresholds["blur_min_warn"]:
        status = "Warning"
        message = "Moderate sharpness; fine print may be difficult to read."
    else:
        status = "Retake Recommended"
        message = "Blur detected (motion or defocus). Focus on commodity text."

    return {
        "metric": "sharpness",
        "name": "Sharpness (Focus)",
        "value": round(variance, 2),
        "score": round(score, 1),
        "unit": "var(Laplacian)",
        "threshold_pass": thresholds["blur_min_pass"],
        "threshold_warn": thresholds["blur_min_warn"],
        "status": status,
        "message": message,
    }


def evaluate_exposure(
    gray: np.ndarray,
    thresholds: Dict[str, float] = DEFAULT_THRESHOLDS,
) -> Dict[str, Any]:
    """
    Evaluate lighting and exposure balance.
    Detects underexposed shadows or blown-out highlights.
    """
    total_pixels = float(gray.size)
    mean_val = float(gray.mean())

    dark_pixels = float(np.sum(gray < 25))
    dark_ratio = dark_pixels / total_pixels

    bright_pixels = float(np.sum(gray > 240))
    bright_ratio = bright_pixels / total_pixels

    if mean_val < thresholds["underexposure_mean_fail"] or dark_ratio > thresholds["dark_pixels_max_ratio"]:
        status = "Retake Recommended"
        message = "Severe underexposure; scene is too dark for optical declaration screening."
    elif mean_val > thresholds["overexposure_mean_fail"] or bright_ratio > thresholds["bright_pixels_max_ratio"]:
        status = "Retake Recommended"
        message = "Severe overexposure; declarations washed out by excessive lighting."
    elif mean_val < thresholds["underexposure_mean_min"] or mean_val > thresholds["overexposure_mean_max"]:
        status = "Warning"
        message = "Sub-optimal lighting balance; adjust ambient light or distance."
    else:
        status = "Pass"
        message = "Balanced exposure across packaging face."

    score = float(max(0.0, 100.0 - abs(mean_val - 128.0) * 0.75))

    return {
        "metric": "exposure",
        "name": "Lighting & Exposure",
        "value": round(mean_val, 1),
        "score": round(score, 1),
        "unit": "mean(intensity)",
        "dark_ratio_pct": round(dark_ratio * 100, 1),
        "bright_ratio_pct": round(bright_ratio * 100, 1),
        "status": status,
        "message": message,
    }


def evaluate_contrast(
    gray: np.ndarray,
    thresholds: Dict[str, float] = DEFAULT_THRESHOLDS,
) -> Dict[str, Any]:
    """
    Evaluate contrast using standard deviation of pixel intensities (RMS contrast).
    Low contrast indicates washed out or hazy image where text lacks separation from background.
    """
    std_val = float(gray.std())
    score = float(min(100.0, max(0.0, (std_val / 65.0) * 100.0)))

    if std_val >= thresholds["contrast_min_pass"]:
        status = "Pass"
        message = "Sufficient contrast between text declarations and packaging background."
    elif std_val >= thresholds["contrast_min_warn"]:
        status = "Warning"
        message = "Low dynamic range; some characters may blend into artwork."
    else:
        status = "Retake Recommended"
        message = "Insufficient contrast; image appears washed out or uniform."

    return {
        "metric": "contrast",
        "name": "Contrast & Readability",
        "value": round(std_val, 1),
        "score": round(score, 1),
        "unit": "std(intensity)",
        "threshold_pass": thresholds["contrast_min_pass"],
        "threshold_warn": thresholds["contrast_min_warn"],
        "status": status,
        "message": message,
    }


def evaluate_resolution(
    width: int,
    height: int,
    thresholds: Dict[str, float] = DEFAULT_THRESHOLDS,
) -> Dict[str, Any]:
    """
    Evaluate spatial resolution against minimum readable requirements.
    """
    total_mp = (width * height) / 1_000_000.0

    min_w = int(thresholds["min_width"])
    min_h = int(thresholds["min_height"])
    rec_w = int(thresholds["recommended_width"])
    rec_h = int(thresholds["recommended_height"])

    if width < min_w or height < min_h:
        status = "Retake Recommended"
        message = f"Resolution ({width}x{height}) is below minimum {min_w}x{min_h} standard."
        score = 30.0
    elif width < rec_w or height < rec_h:
        status = "Warning"
        message = f"Acceptable resolution ({width}x{height}); ideal is {rec_w}x{rec_h} or higher."
        score = 75.0
    else:
        status = "Pass"
        message = f"High resolution capture ({width}x{height}, {total_mp:.2f} MP)."
        score = 100.0

    return {
        "metric": "resolution",
        "name": "Resolution & Dimensions",
        "width": width,
        "height": height,
        "total_megapixels": round(total_mp, 2),
        "score": round(score, 1),
        "status": status,
        "message": message,
    }


def evaluate_glare(
    gray: np.ndarray,
    thresholds: Dict[str, float] = DEFAULT_THRESHOLDS,
) -> Dict[str, Any]:
    """
    Evaluate specular reflections and high-intensity clipped glare spots.
    Hotspots on glossy plastic / foil conceal critical declarations (e.g. MRP, date).
    """
    total_pixels = float(gray.size)
    glare_pixels = float(np.sum(gray >= 252))
    glare_pct = (glare_pixels / total_pixels) * 100.0

    score = float(max(0.0, 100.0 - (glare_pct * 5.0)))

    if glare_pct >= thresholds["glare_max_fail_pct"]:
        status = "Retake Recommended"
        message = f"Severe glare hotspot ({glare_pct:.1f}% frame area). Tilt packaging away from direct light."
    elif glare_pct >= thresholds["glare_max_warn_pct"]:
        status = "Warning"
        message = f"Localized glare detected ({glare_pct:.1f}% frame area). Check that text is not obscured."
    else:
        status = "Pass"
        message = "No significant specular glare or reflective hotspots."

    return {
        "metric": "glare",
        "name": "Glare & Specular Reflections",
        "value": round(glare_pct, 2),
        "score": round(score, 1),
        "unit": "% saturated area",
        "status": status,
        "message": message,
    }


def assess_image_quality(
    image_input: Union[bytes, np.ndarray],
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Run comprehensive image quality assessment on image bytes or BGR ndarray.
    Returns composite score, categorized metrics, overall status, and actionable recommendations.
    """
    t = DEFAULT_THRESHOLDS.copy()
    if thresholds:
        t.update(thresholds)

    # 1. Decode image if bytes
    if isinstance(image_input, bytes):
        if len(image_input) == 0:
            return _create_error_assessment("Empty image input.")
        nparr = np.frombuffer(image_input, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return _create_error_assessment("Could not decode image bytes (invalid/corrupted image).")
    elif isinstance(image_input, np.ndarray):
        img = image_input
    else:
        return _create_error_assessment(f"Unsupported image input type: {type(image_input)}")

    height, width = img.shape[:2]
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # 2. Evaluate individual quality pillars
    sharpness = evaluate_sharpness(gray, t)
    exposure = evaluate_exposure(gray, t)
    contrast = evaluate_contrast(gray, t)
    resolution = evaluate_resolution(width, height, t)
    glare = evaluate_glare(gray, t)

    metrics_list = [sharpness, exposure, contrast, resolution, glare]

    # 3. Overall status determination
    has_retake = any(m["status"] == "Retake Recommended" for m in metrics_list)
    has_warning = any(m["status"] == "Warning" for m in metrics_list)

    if has_retake:
        overall_status = "Retake Recommended"
        is_acceptable = False
    elif has_warning:
        overall_status = "Warning"
        is_acceptable = True
    else:
        overall_status = "Pass"
        is_acceptable = True

    # Composite quality score (0 to 100)
    # Weights: Sharpness (35%), Exposure (25%), Contrast (20%), Glare (10%), Resolution (10%)
    composite_score = round(
        sharpness["score"] * 0.35
        + exposure["score"] * 0.25
        + contrast["score"] * 0.20
        + glare["score"] * 0.10
        + resolution["score"] * 0.10,
        1,
    )

    # 4. Generate actionable inspector recommendations
    recommendations: List[str] = []
    if sharpness["status"] != "Pass":
        recommendations.append("Hold device steady and tap to focus on small text (e.g. Net Qty or MRP).")
    if exposure["status"] == "Retake Recommended":
        if exposure["value"] < t["underexposure_mean_fail"]:
            recommendations.append("Increase ambient lighting or move to a well-lit inspection bay.")
        else:
            recommendations.append("Reduce harsh direct light or move away from bright lamp reflection.")
    elif exposure["status"] == "Warning":
        recommendations.append("Adjust camera angle to balance illumination across the entire package face.")
    if contrast["status"] != "Pass":
        recommendations.append("Ensure background is neutral and package declarations are visibly distinct.")
    if glare["status"] != "Pass":
        recommendations.append("Tilt package slightly (10-15 degrees) to deflect specular glare from glossy packaging.")
    if resolution["status"] != "Pass":
        recommendations.append("Position device closer so package occupies at least 65% of the camera frame.")

    if not recommendations:
        recommendations.append("Image quality is optimal for optical screening and calibration.")

    return {
        "overall_status": overall_status,
        "is_acceptable": is_acceptable,
        "composite_score": composite_score,
        "metrics": {
            "sharpness": sharpness,
            "exposure": exposure,
            "contrast": contrast,
            "resolution": resolution,
            "glare": glare,
        },
        "recommendations": recommendations,
        "thresholds_used": t,
        "disclaimer": LEGAL_METROLOGY_QUALITY_DISCLAIMER,
    }


def _create_error_assessment(error_message: str) -> Dict[str, Any]:
    """Fallback assessment for corrupted or empty images."""
    return {
        "overall_status": "Retake Recommended",
        "is_acceptable": False,
        "composite_score": 0.0,
        "metrics": {
            "sharpness": {"metric": "sharpness", "status": "Retake Recommended", "value": 0.0, "score": 0.0, "message": error_message},
            "exposure": {"metric": "exposure", "status": "Retake Recommended", "value": 0.0, "score": 0.0, "message": error_message},
            "contrast": {"metric": "contrast", "status": "Retake Recommended", "value": 0.0, "score": 0.0, "message": error_message},
            "resolution": {"metric": "resolution", "status": "Retake Recommended", "width": 0, "height": 0, "score": 0.0, "message": error_message},
            "glare": {"metric": "glare", "status": "Retake Recommended", "value": 100.0, "score": 0.0, "message": error_message},
        },
        "recommendations": [f"Image invalid: {error_message}. Please retake photograph."],
        "thresholds_used": DEFAULT_THRESHOLDS,
        "disclaimer": LEGAL_METROLOGY_QUALITY_DISCLAIMER,
    }
