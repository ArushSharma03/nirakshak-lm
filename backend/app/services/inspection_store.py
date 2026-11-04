"""
Inspection storage and repository service.

Implements dual-mode persistence:
1. Database Mode: Uses PostgreSQL via SQLAlchemy when the database is available.
2. Safe Fallback / Demo Mode: Stores inspections in an in-memory/JSON store when PostgreSQL is offline,
   guaranteeing that API calls never throw 500 errors and inspections can be created, retrieved,
   and populated with captured view images.
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.core.config import settings

# In-memory store for fallback/demo mode
_MEMORY_INSPECTIONS: Dict[str, Dict[str, Any]] = {}
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
FALLBACK_FILE = os.path.join(DATA_DIR, "inspections_store.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_persisted_fallback():
    global _MEMORY_INSPECTIONS
    if os.path.exists(FALLBACK_FILE):
        try:
            with open(FALLBACK_FILE, "r", encoding="utf-8") as f:
                _MEMORY_INSPECTIONS = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load fallback inspections: {e}")


def _save_persisted_fallback():
    _ensure_data_dir()
    try:
        with open(FALLBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(_MEMORY_INSPECTIONS, f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: Failed to persist fallback inspections: {e}")


# Initialize fallback store
_load_persisted_fallback()


def is_database_available() -> bool:
    """Check if the configured PostgreSQL database is reachable."""
    try:
        from app.db.session import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


def create_inspection_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new inspection record.
    Uses PostgreSQL if available, otherwise saves to the persistent local fallback store.
    """
    inspection_id = payload.get("id") or f"INS-{datetime.now().year}-{str(uuid.uuid4())[:8].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()

    record = {
        "id": inspection_id,
        "product_name": payload.get("product_name") or "Generic Commodity Sample",
        "product_category": payload.get("product_category") or "food_grocery",
        "brand": payload.get("brand") or "Unspecified Manufacturer",
        "declared_net_qty": payload.get("declared_net_qty") or "100 g",
        "declared_mrp": float(payload.get("declared_mrp") or 50.0),
        "location": payload.get("location") or "Retail Inspection Bay 1",
        "inspector_name": payload.get("inspector_name") or "Mr. Arush Sharma",
        "status": "created",
        "final_outcome": "Manual Review Required",
        "notes": payload.get("notes") or "",
        "timestamp": now_iso,
        "views_captured": payload.get("views_captured") or {"front": False, "rear": False, "side": False},
        "marker_detected": bool(payload.get("marker_detected", False)),
        "scale_ppm": payload.get("scale_ppm"),
        "images": payload.get("images") or {},
        "database_saved": False,
        "mode": "Demo / Offline Fallback",
    }

    # Attempt PostgreSQL persistence if DB is available
    if is_database_available():
        try:
            from app.db.session import SessionLocal
            from app.models import Inspection, Product, InspectionStatus, User

            db = SessionLocal()
            try:
                # Find or create a default demo user for tracking
                user = db.query(User).first()
                if not user:
                    user = User(
                        username="inspector_default",
                        email="inspector@nirikshak.gov.in",
                        hashed_password="mock_password",
                        full_name=record["inspector_name"],
                    )
                    db.add(user)
                    db.flush()

                product = Product(
                    name=record["product_name"],
                    category=record["product_category"],
                    description=f"Brand: {record['brand']}",
                )
                db.add(product)
                db.flush()

                db_insp = Inspection(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    product_id=product.id,
                    status=InspectionStatus.CREATED,
                    notes=record["notes"],
                )
                db.add(db_insp)
                db.commit()
                record["database_saved"] = True
                record["mode"] = "Live PostgreSQL"
                record["db_id"] = str(db_insp.id)
            finally:
                db.close()
        except Exception as e:
            print(f"Database save error (falling back to offline store): {e}")
            record["database_saved"] = False
            record["mode"] = "Demo / Offline Fallback"

    # Always mirror in local store so offline and demonstrator workflows never lose data
    _MEMORY_INSPECTIONS[inspection_id] = record
    _save_persisted_fallback()

    return record


def get_inspection_record(inspection_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve an inspection by its ID."""
    return _MEMORY_INSPECTIONS.get(inspection_id)


def list_inspection_records() -> List[Dict[str, Any]]:
    """List all stored inspection records ordered by timestamp descending."""
    return sorted(
        list(_MEMORY_INSPECTIONS.values()),
        key=lambda r: r.get("timestamp", ""),
        reverse=True,
    )


from app.services.quality_assessor import assess_image_quality
from app.services.preprocessor import preprocess_package_image


def attach_inspection_image(
    inspection_id: str,
    view_type: str,
    image_bytes: bytes,
    original_filename: str = "capture.jpg",
    marker_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Attach a captured package image to an existing inspection record.
    1. Preserves raw image evidence unchanged under data/images/{inspection_id}_{view_type}.jpg.
    2. Runs comprehensive Image Quality Assessment (sharpness, exposure, contrast, resolution, glare).
    3. Executes reproducible Image Preprocessing pipeline and stores processed copy as
       data/images/{inspection_id}_{view_type}_processed.jpg.
    4. Updates inspection record metadata with hashes, metrics, and calibration data.
    """
    _ensure_data_dir()
    images_dir = os.path.join(DATA_DIR, "images")
    os.makedirs(images_dir, exist_ok=True)

    file_hash = hashlib.sha256(image_bytes).hexdigest()
    filename = f"{inspection_id}_{view_type}.jpg"
    filepath = os.path.join(images_dir, filename)

    # 1. Preserve raw evidence byte-for-byte
    with open(filepath, "wb") as f:
        f.write(image_bytes)

    # 2. Quality Assessment
    quality_assessment = assess_image_quality(image_bytes)

    # 3. Image Preprocessing
    preproc_res = preprocess_package_image(image_bytes)
    processed_meta: Optional[Dict[str, Any]] = None

    if preproc_res.get("success"):
        proc_filename = f"{inspection_id}_{view_type}_processed.jpg"
        proc_filepath = os.path.join(images_dir, proc_filename)
        with open(proc_filepath, "wb") as f:
            f.write(preproc_res["processed_bytes"])

        processed_meta = {
            "filename": proc_filename,
            "filepath": proc_filepath,
            "processed_filename": proc_filename,
            "processed_filepath": proc_filepath,
            "file_hash": preproc_res["processed_file_hash"],
            "algorithm_version": preproc_res["algorithm_version"],
            "steps_applied": preproc_res["steps_applied"],
            "perspective_rectified": preproc_res["perspective_rectified"],
            "perspective_reason": preproc_res["perspective_reason"],
            "original_dimensions": preproc_res["original_dimensions"],
            "processed_dimensions": preproc_res["processed_dimensions"],
            "timestamp": preproc_res["timestamp"],
        }

    record = _MEMORY_INSPECTIONS.get(inspection_id)
    if not record:
        record = create_inspection_record({"id": inspection_id})

    # Update views_captured
    if "views_captured" not in record or not isinstance(record["views_captured"], dict):
        record["views_captured"] = {"front": False, "rear": False, "side": False}
    record["views_captured"][view_type] = True

    # Update images dict
    if "images" not in record or not isinstance(record["images"], dict):
        record["images"] = {}

    image_meta = {
        "view_type": view_type,
        "filename": filename,
        "filepath": filepath,
        "original_filename": original_filename,
        "file_hash": file_hash,
        "size_bytes": len(image_bytes),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "marker_detected": marker_result.get("detected", False) if marker_result else False,
        "marker_score": marker_result.get("score") if marker_result else None,
        "pixel_width": marker_result.get("pixel_width") if marker_result else None,
        "pixel_height": marker_result.get("pixel_height") if marker_result else None,
        "estimated_ppm": marker_result.get("estimated_ppm") if marker_result else None,
        "quality_assessment": quality_assessment,
        "preprocessing": processed_meta,
    }
    record["images"][view_type] = image_meta

    if image_meta["marker_detected"]:
        record["marker_detected"] = True
        if image_meta["estimated_ppm"]:
            record["scale_ppm"] = image_meta["estimated_ppm"]

    # Check if all views captured
    if (
        record["views_captured"].get("front")
        and record["views_captured"].get("rear")
        and record["views_captured"].get("side")
    ):
        record["status"] = "images_uploaded"

    _MEMORY_INSPECTIONS[inspection_id] = record
    _save_persisted_fallback()

    return record
