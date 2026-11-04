"""
Comprehensive test suite for Nirikshak-LM ArUco Reference Marker Detection.

Covers:
1. Synthetic Tests (Pure Marker Generation, Quiet Zone, Contrast, Alternate Dictionaries, Negative Cases)
2. Captured-Image / Simulated Webcam Scene Tests (1280x720 Realistic Packaging Frame)
3. HTTP Integration Tests for FastAPI endpoints (/health, /capture/detect-marker, /capture/reference-marker)
"""

import sys
import os
import io
import urllib.request
import json
import cv2
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.marker_detector import (
    detect_marker,
    generate_reference_marker_image,
    _DEFAULT_DICT,
)


def run_synthetic_tests():
    print("=" * 60)
    print("RUNNING PART 1: SYNTHETIC TESTS")
    print("=" * 60)

    # 1. Positive Test: Clean ArUco 4x4_50 ID 0 with white quiet zone margin
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_raw = np.zeros((300, 300), dtype=np.uint8)
    cv2.aruco.generateImageMarker(aruco_dict, 0, 300, marker_raw, 1)
    marker_padded = cv2.copyMakeBorder(marker_raw, 50, 50, 50, 50, cv2.BORDER_CONSTANT, value=255)
    _, buf = cv2.imencode(".jpg", marker_padded)

    res1 = detect_marker(buf.tobytes(), expected_marker_mm=50.0)
    assert res1.detected is True, "Synthetic Test 1 Failed: Marker not detected"
    assert res1.marker_id == 0, f"Synthetic Test 1 Failed: Expected ID 0, got {res1.marker_id}"
    assert res1.score is not None and res1.score >= 0.95, f"Synthetic Test 1 Failed: Low score {res1.score}"
    assert res1.estimated_ppm is not None and res1.estimated_ppm > 0, "Synthetic Test 1 Failed: No PPM"
    print(f"PASS: Synthetic Test 1 (Clean ArUco 4x4_50 ID 0) -> ID={res1.marker_id}, Score={res1.score}, Scale={res1.estimated_ppm} px/mm")

    # 2. Dim / Low-Contrast Synthetic Test (CLAHE branch verification)
    dim_img = (marker_padded.astype(np.float32) * 0.35 + 20).astype(np.uint8)
    _, buf_dim = cv2.imencode(".jpg", dim_img)
    res2 = detect_marker(buf_dim.tobytes())
    assert res2.detected is True, "Synthetic Test 2 Failed: Dim marker not detected"
    assert res2.marker_id == 0, "Synthetic Test 2 Failed: Expected ID 0"
    print(f"PASS: Synthetic Test 2 (Low-Contrast CLAHE Pass) -> ID={res2.marker_id}, Score={res2.score}")

    # 3. Cross-Dictionary Fallback Test: ArUco 4x4_100 ID 75 (outside 4x4_50 range)
    dict_100 = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)
    marker_100 = np.zeros((300, 300), dtype=np.uint8)
    cv2.aruco.generateImageMarker(dict_100, 75, 300, marker_100, 1)
    padded_100 = cv2.copyMakeBorder(marker_100, 50, 50, 50, 50, cv2.BORDER_CONSTANT, value=255)
    _, buf_100 = cv2.imencode(".jpg", padded_100)
    res3 = detect_marker(buf_100.tobytes())
    assert res3.detected is True, "Synthetic Test 3 Failed: Cross-dictionary marker not detected"
    assert res3.marker_id == 75, f"Synthetic Test 3 Failed: Expected ID 75, got {res3.marker_id}"
    assert "4x4_100" in res3.dictionary, f"Synthetic Test 3 Failed: Dictionary mismatch {res3.dictionary}"
    print(f"PASS: Synthetic Test 3 (Cross-Dictionary Fallback) -> Dict={res3.dictionary}, ID={res3.marker_id}")

    # 4. Negative Test: Blank/textured image with no marker
    blank_img = np.full((400, 400), 210, dtype=np.uint8)
    cv2.putText(blank_img, "Packaged Commodity Sample", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 50, 2)
    _, buf_blank = cv2.imencode(".jpg", blank_img)
    res4 = detect_marker(buf_blank.tobytes())
    assert res4.detected is False, "Synthetic Test 4 Failed: False positive detected"
    assert "not detected" in res4.message.lower(), "Synthetic Test 4 Failed: Unexpected failure message"
    print(f"PASS: Synthetic Test 4 (Negative Scene without Marker) -> detected=False, message='{res4.message[:45]}...'")


def run_captured_camera_scene_tests():
    print("\n" + "=" * 60)
    print("RUNNING PART 2: REALISTIC CAPTURED-SCENE TESTS")
    print("=" * 60)

    # Simulate a realistic 1280x720 webcam capture frame of a product table:
    # Background surface (wooden/white inspection desk)
    scene = np.full((720, 1280, 3), 235, dtype=np.uint8)
    # Lighting gradient across the surface
    for y in range(720):
        scene[y, :, :] = np.clip(scene[y, :, :].astype(int) - int((y / 720.0) * 35), 0, 255).astype(np.uint8)

    # Draw a simulated packaged commodity box (Britannia biscuit packet) in center
    cv2.rectangle(scene, (250, 180), (750, 560), (40, 60, 190), -1)
    cv2.rectangle(scene, (250, 180), (750, 560), (20, 30, 120), 3)
    cv2.putText(scene, "BRITANNIA GOOD DAY", (280, 250), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
    cv2.putText(scene, "Butter Cookies 100g", (280, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240, 240, 240), 1)

    # Save camera scene WITHOUT marker (Scenario A: user captures only the package)
    _, buf_scene_no_marker = cv2.imencode(".jpg", scene)
    res_a = detect_marker(buf_scene_no_marker.tobytes())
    assert res_a.detected is False, "Captured Scene A Failed: False positive detection"
    print(f"PASS: Captured Scene A (Package Only, No Marker) -> detected=False, Guidance displayed")

    # Scenario B: Place the 50mm ArUco reference marker coplanar beside the package (x: 820..1060, y: 240..480)
    marker_png = generate_reference_marker_image(marker_id=0, size_px=200, margin_px=25)
    marker_arr = cv2.imdecode(np.frombuffer(marker_png, np.uint8), cv2.IMREAD_COLOR)
    mh, mw, _ = marker_arr.shape
    scene[240:240+mh, 820:820+mw] = marker_arr

    _, buf_scene_with_marker = cv2.imencode(".jpg", scene)
    res_b = detect_marker(buf_scene_with_marker.tobytes(), expected_marker_mm=50.0)
    assert res_b.detected is True, "Captured Scene B Failed: Marker beside package was not detected"
    assert res_b.marker_id == 0, f"Captured Scene B Failed: Expected ID 0, got {res_b.marker_id}"
    assert res_b.score is not None and res_b.score >= 0.90, f"Captured Scene B Failed: Low score {res_b.score}"
    assert res_b.pixel_width is not None and 180 <= res_b.pixel_width <= 220, f"Captured Scene B: Unexpected px_width {res_b.pixel_width}"
    print(f"PASS: Captured Scene B (Package + Coplanar 50mm Marker) -> detected=True, ID={res_b.marker_id}, Score={res_b.score}, Scale={res_b.estimated_ppm} px/mm")


def run_http_integration_tests():
    print("\n" + "=" * 60)
    print("RUNNING PART 3: HTTP API INTEGRATION TESTS (http://127.0.0.1:8000)")
    print("=" * 60)

    # 1. Health check
    req = urllib.request.Request("http://127.0.0.1:8000/health")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        health_data = json.loads(resp.read().decode("utf-8"))
        assert health_data.get("status") == "healthy"
        print(f"PASS: GET /health -> Status 200, Backend Version: {health_data.get('version', 'unknown')}")

    # 2. Reference marker info check
    req_info = urllib.request.Request("http://127.0.0.1:8000/capture/reference-marker/info")
    with urllib.request.urlopen(req_info) as resp:
        assert resp.status == 200
        info_data = json.loads(resp.read().decode("utf-8"))
        assert info_data.get("standard_dictionary") == "ArUco 4x4_50"
        assert info_data.get("physical_dimension_mm") == 50.0
        print(f"PASS: GET /capture/reference-marker/info -> Dictionary: {info_data['standard_dictionary']}, Size: {info_data['physical_dimension_mm']}mm")

    # 3. Reference marker image download check
    req_img = urllib.request.Request("http://127.0.0.1:8000/capture/reference-marker")
    with urllib.request.urlopen(req_img) as resp:
        assert resp.status == 200
        assert resp.headers.get("content-type") == "image/png"
        img_bytes = resp.read()
        assert len(img_bytes) > 5000, "Downloaded marker image too small"
        print(f"PASS: GET /capture/reference-marker -> Status 200, PNG Content ({len(img_bytes)} bytes)")

    # 4. POST /capture/detect-marker with downloaded marker
    boundary = "----TestBoundaryNirikshakLM77123"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="marker.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + img_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req_post = urllib.request.Request(
        "http://127.0.0.1:8000/capture/detect-marker",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req_post) as resp:
        assert resp.status == 200
        post_data = json.loads(resp.read().decode("utf-8"))
        assert post_data.get("detected") is True
        assert post_data.get("marker_id") == 0
        assert post_data.get("pixel_width") is not None
        print(f"PASS: POST /capture/detect-marker (Positive) -> detected=True, ID={post_data['marker_id']}, PPM={post_data.get('estimated_ppm')} px/mm")

    # 5. POST /capture/detect-marker with negative image
    blank_raw = np.full((300, 300, 3), 220, dtype=np.uint8)
    _, blank_bytes = cv2.imencode(".jpg", blank_raw)
    body_neg = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="blank.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + blank_bytes.tobytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req_neg = urllib.request.Request(
        "http://127.0.0.1:8000/capture/detect-marker",
        data=body_neg,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req_neg) as resp:
        assert resp.status == 200
        neg_data = json.loads(resp.read().decode("utf-8"))
        assert neg_data.get("detected") is False
        print(f"PASS: POST /capture/detect-marker (Negative) -> detected=False, message='{neg_data['message'][:45]}...'")


if __name__ == "__main__":
    run_synthetic_tests()
    run_captured_camera_scene_tests()
    run_http_integration_tests()
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)
