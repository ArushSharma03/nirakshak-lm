"""
Automated Test Suite for Week 3: Image Preprocessing and Quality Assessment.

Tests:
1. Sharp vs Blurred images (Laplacian variance detection).
2. Dark (underexposed), Overexposed, and Low-Contrast images.
3. Glare hotspot detection on specular reflections.
4. Valid vs Corrupt / Invalid image files.
5. Original evidence preservation (SHA-256 byte-for-byte integrity check).
6. Preprocessing output validity (separate processed copy, contrast enhancement, bilateral filter).
7. Perspective correction success on known quadrilateral.
8. Perspective correction safe-skip behavior on irregular scenes (avoid text distortion).
9. API integration for Front, Rear, and Side images with quality assessment and processed image retrieval.

NOTE: Tests 1-8 use controlled synthetic images with mathematically known properties.
Test 9 executes integration tests against the running FastAPI service.
"""

import os
import sys
import unittest
import hashlib
import cv2
import numpy as np

# Ensure backend root is on sys.path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.quality_assessor import assess_image_quality, evaluate_sharpness, evaluate_exposure, evaluate_contrast, evaluate_glare
from app.services.preprocessor import preprocess_package_image, detect_package_quadrilateral, rectify_perspective, ALGORITHM_VERSION


class TestImageQualityAssessment(unittest.TestCase):
    """Controlled synthetic tests for image quality assessment."""

    def test_sharp_vs_blurred_images(self):
        """Test variance of Laplacian correctly distinguishes sharp from blurred images."""
        # 1. Create a sharp image with high-contrast text and edge patterns
        sharp = np.full((500, 500, 3), 240, dtype=np.uint8)
        for i in range(20, 480, 40):
            cv2.line(sharp, (i, 20), (i, 480), (10, 10, 10), 3)
            cv2.putText(sharp, f"NET QTY 100g {i}", (50, i), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

        # 2. Create a heavily blurred version
        blurred = cv2.GaussianBlur(sharp, (31, 31), 10.0)

        res_sharp = assess_image_quality(sharp)
        res_blur = assess_image_quality(blurred)

        # Sharp image must have high variance and Pass
        self.assertGreater(res_sharp["metrics"]["sharpness"]["value"], 120.0)
        self.assertEqual(res_sharp["metrics"]["sharpness"]["status"], "Pass")

        # Blurred image must have low variance and Retake Recommended
        self.assertLess(res_blur["metrics"]["sharpness"]["value"], 60.0)
        self.assertEqual(res_blur["metrics"]["sharpness"]["status"], "Retake Recommended")
        self.assertEqual(res_blur["overall_status"], "Retake Recommended")
        self.assertTrue(any("focus" in r.lower() or "steady" in r.lower() for r in res_blur["recommendations"]))

    def test_dark_underexposed_image(self):
        """Test detection of dark / underexposed photographs."""
        # Near black image
        dark = np.full((400, 400, 3), 20, dtype=np.uint8)
        res = assess_image_quality(dark)

        self.assertEqual(res["metrics"]["exposure"]["status"], "Retake Recommended")
        self.assertEqual(res["overall_status"], "Retake Recommended")
        self.assertTrue(any("light" in r.lower() for r in res["recommendations"]))

    def test_overexposed_image(self):
        """Test detection of washed-out / overexposed photographs."""
        # Blown out white image
        bright = np.full((400, 400, 3), 245, dtype=np.uint8)
        res = assess_image_quality(bright)

        self.assertEqual(res["metrics"]["exposure"]["status"], "Retake Recommended")
        self.assertEqual(res["overall_status"], "Retake Recommended")

    def test_low_contrast_image(self):
        """Test detection of low-contrast, washed-out images."""
        # Uniform gray with very subtle delta (std around ~3.5)
        low_contrast = np.full((400, 400, 3), 128, dtype=np.uint8)
        low_contrast[0:200, 0:200] = 134

        res = assess_image_quality(low_contrast)
        self.assertEqual(res["metrics"]["contrast"]["status"], "Retake Recommended")
        self.assertLess(res["metrics"]["contrast"]["value"], 25.0)

    def test_glare_hotspot_detection(self):
        """Test detection of specular reflections / glare hotspots."""
        scene = np.full((400, 400, 3), 120, dtype=np.uint8)
        # Create a large glare hotspot (20% of frame area)
        cv2.circle(scene, (200, 200), 90, (255, 255, 255), -1)

        res = assess_image_quality(scene)
        self.assertEqual(res["metrics"]["glare"]["status"], "Retake Recommended")
        self.assertGreater(res["metrics"]["glare"]["value"], 15.0)
        self.assertTrue(any("glare" in r.lower() for r in res["recommendations"]))

    def test_resolution_minimum_thresholds(self):
        """Test resolution evaluation flags frames smaller than 640x480."""
        tiny = np.full((200, 200, 3), 150, dtype=np.uint8)
        res = assess_image_quality(tiny)
        self.assertEqual(res["metrics"]["resolution"]["status"], "Retake Recommended")

        hd = np.full((720, 1280, 3), 150, dtype=np.uint8)
        res_hd = assess_image_quality(hd)
        self.assertEqual(res_hd["metrics"]["resolution"]["status"], "Pass")

    def test_invalid_and_corrupt_images(self):
        """Test that invalid/corrupt image inputs are safely handled without throwing uncaught exceptions."""
        empty_res = assess_image_quality(b"")
        self.assertEqual(empty_res["overall_status"], "Retake Recommended")
        self.assertFalse(empty_res["is_acceptable"])

        corrupt_res = assess_image_quality(b"random-non-image-junk-bytes-12345")
        self.assertEqual(corrupt_res["overall_status"], "Retake Recommended")
        self.assertFalse(corrupt_res["is_acceptable"])


class TestImagePreprocessingPipeline(unittest.TestCase):
    """Tests for reproducible, evidence-preserving image preprocessing."""

    def test_corrupt_input_handling(self):
        """Test preprocessing gracefully fails on corrupted input."""
        res = preprocess_package_image(b"corrupted-bytes-xyz")
        self.assertFalse(res["success"])
        self.assertIn("error", res)

    def test_original_evidence_preservation(self):
        """Test that original raw image bytes are completely preserved and untouched."""
        # Create sample image
        img = np.full((480, 640, 3), 180, dtype=np.uint8)
        cv2.putText(img, "BRITANNIA 100g", (100, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
        _, raw_enc = cv2.imencode(".jpg", img)
        raw_bytes = raw_enc.tobytes()
        original_hash = hashlib.sha256(raw_bytes).hexdigest()

        # Run preprocessing
        res = preprocess_package_image(raw_bytes)
        self.assertTrue(res["success"])

        # Check raw hash recorded matches
        self.assertEqual(res["raw_file_hash"], original_hash)

        # Processed bytes must be distinct (contrast-enhanced / filtered)
        self.assertNotEqual(res["processed_file_hash"], original_hash)
        self.assertGreater(len(res["processed_bytes"]), 0)

        # Check raw bytes were not altered
        self.assertEqual(hashlib.sha256(raw_bytes).hexdigest(), original_hash)

    def test_preprocessing_steps_and_metadata(self):
        """Test that preprocessing applies grayscale, bilateral denoise, and CLAHE, returning versioned metadata."""
        img = np.full((480, 640, 3), 160, dtype=np.uint8)
        cv2.putText(img, "SAMPLE EVIDENCE", (80, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (10, 10, 10), 2)
        _, enc = cv2.imencode(".jpg", img)

        res = preprocess_package_image(enc.tobytes())
        self.assertTrue(res["success"])
        self.assertEqual(res["algorithm_version"], ALGORITHM_VERSION)
        self.assertIn("grayscale_conversion", res["steps_applied"])
        self.assertIn("bilateral_denoising", res["steps_applied"])
        self.assertIn("clahe_contrast_enhancement", res["steps_applied"])
        self.assertEqual(res["original_dimensions"], [640, 480])

        # Verify decoded processed image is valid JPEG
        decoded = cv2.imdecode(np.frombuffer(res["processed_bytes"], np.uint8), cv2.IMREAD_COLOR)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded.shape[0], 480)
        self.assertEqual(decoded.shape[1], 640)

    def test_perspective_rectification_on_valid_quadrilateral(self):
        """Test perspective correction is successfully triggered when a clean convex quadrilateral is present."""
        # Scene with a prominent skewed package polygon (40% of frame area)
        scene = np.full((600, 800, 3), 235, dtype=np.uint8)
        quad_pts = np.array([[150, 100], [650, 120], [680, 500], [130, 480]], dtype=np.int32)
        cv2.fillPoly(scene, [quad_pts], (40, 40, 40))
        cv2.putText(scene, "PACKAGING FACE", (250, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        _, enc = cv2.imencode(".jpg", scene)
        res = preprocess_package_image(enc.tobytes(), enable_perspective_correction=True)

        self.assertTrue(res["success"])
        self.assertTrue(res["perspective_rectified"])
        self.assertIn("perspective_rectification", res["steps_applied"])

    def test_safe_skip_perspective_on_irregular_scene(self):
        """Test perspective rectification is safely skipped when no clear quadrilateral exists (avoids distortion)."""
        # Plain scene without a 4-point quadrilateral (e.g. circle or textured background)
        scene = np.full((600, 800, 3), 200, dtype=np.uint8)
        cv2.circle(scene, (400, 300), 150, (50, 50, 50), -1)

        _, enc = cv2.imencode(".jpg", scene)
        res = preprocess_package_image(enc.tobytes(), enable_perspective_correction=True)

        self.assertTrue(res["success"])
        self.assertFalse(res["perspective_rectified"])
        self.assertIn("skipped", res["perspective_reason"].lower())
        self.assertNotIn("perspective_rectification", res["steps_applied"])


class TestApiIntegration(unittest.TestCase):
    """Integration tests verifying HTTP endpoints for quality assessment and preprocessing."""

    @classmethod
    def setUpClass(cls):
        # Verify local server is reachable
        import urllib.request
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as resp:
                cls.server_online = (resp.status == 200)
        except Exception:
            cls.server_online = False

    def test_quality_assessment_endpoint(self):
        """Test POST /capture/assess-quality returns structured metrics and recommendations."""
        if not self.server_online:
            self.skipTest("FastAPI server offline on localhost:8000")

        import subprocess
        import json

        # Create a test sharp image
        sharp = np.full((480, 640, 3), 230, dtype=np.uint8)
        cv2.putText(sharp, "AMUL BUTTER 500G", (100, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
        test_file = "test_quality_api.jpg"
        cv2.imwrite(test_file, sharp)

        try:
            cmd = [
                "curl.exe", "-s", "-X", "POST",
                "http://127.0.0.1:8000/capture/assess-quality",
                "-F", f"file=@{test_file}",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            data = json.loads(res.stdout)

            self.assertIn("overall_status", data)
            self.assertIn("composite_score", data)
            self.assertIn("metrics", data)
            self.assertIn("sharpness", data["metrics"])
            self.assertIn("exposure", data["metrics"])
            self.assertIn("contrast", data["metrics"])
            self.assertIn("resolution", data["metrics"])
            self.assertIn("glare", data["metrics"])
            self.assertIn("disclaimer", data)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_inspection_view_upload_with_preprocessing_and_quality(self):
        """Test uploading Front, Rear, and Side views generates quality assessment and processed copies."""
        if not self.server_online:
            self.skipTest("FastAPI server offline on localhost:8000")

        import subprocess
        import json
        import urllib.request

        # 1. Create a new inspection
        req = urllib.request.Request(
            "http://127.0.0.1:8000/inspections/",
            data=json.dumps({
                "product_name": "Dettol Original Soap 125g",
                "product_category": "personal_care",
                "brand": "Reckitt Benckiser",
                "declared_net_qty": "125 g",
                "declared_mrp": 58.0,
                "inspector_name": "Inspector Test",
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            rec = json.loads(resp.read().decode())
        ins_id = rec["id"]

        # 2. Upload Front, Rear, and Side images
        test_file = "test_view_temp.jpg"
        for vt in ["front", "rear", "side"]:
            img = np.full((480, 640, 3), 220, dtype=np.uint8)
            cv2.putText(img, f"DETTOL {vt.upper()} PANEL", (80, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (10, 80, 20), 2)
            cv2.imwrite(test_file, img)

            try:
                cmd = [
                    "curl.exe", "-s", "-X", "POST",
                    f"http://127.0.0.1:8000/inspections/{ins_id}/images",
                    "-F", f"view_type={vt}",
                    "-F", f"file=@{test_file}",
                ]
                res = subprocess.run(cmd, capture_output=True, text=True)
                updated = json.loads(res.stdout)

                # Verify view metadata includes quality assessment and preprocessing
                view_meta = updated["images"][vt]
                self.assertIn("quality_assessment", view_meta)
                self.assertIn("preprocessing", view_meta)
                self.assertIsNotNone(view_meta["preprocessing"])
                self.assertEqual(view_meta["preprocessing"]["algorithm_version"], ALGORITHM_VERSION)

                # 3. Verify processed image endpoint GET /inspections/{id}/images/{view}/processed
                proc_url = f"http://127.0.0.1:8000/inspections/{ins_id}/images/{vt}/processed"
                with urllib.request.urlopen(proc_url) as proc_resp:
                    self.assertEqual(proc_resp.status, 200)
                    self.assertEqual(proc_resp.headers.get("content-type"), "image/jpeg")
                    proc_bytes = proc_resp.read()
                    self.assertGreater(len(proc_bytes), 0)

                # 4. Verify quality endpoint GET /inspections/{id}/images/{view}/quality
                qual_url = f"http://127.0.0.1:8000/inspections/{ins_id}/images/{vt}/quality"
                with urllib.request.urlopen(qual_url) as qual_resp:
                    self.assertEqual(qual_resp.status, 200)
                    qual_data = json.loads(qual_resp.read().decode())
                    self.assertIn("overall_status", qual_data)
                    self.assertIn("metrics", qual_data)

            finally:
                if os.path.exists(test_file):
                    os.remove(test_file)


if __name__ == "__main__":
    unittest.main()
