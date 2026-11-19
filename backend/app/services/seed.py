"""Sample inspections shipped with the repository.

`backend/seed/` holds analyzed inspections and their original photos. When the API starts with an
empty store, they are installed so a fresh checkout opens with real data. Enhanced (CLAHE) copies
are rebuilt from the originals rather than stored.

    python -m app.services.seed export   # replace the seed with the current store
"""

import copy
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

from app.services import inspection_store as store
from app.services.preprocessor import preprocess_package_image

SEED_DIR = Path(__file__).resolve().parents[2] / "seed"
SEED_FILE = SEED_DIR / "inspections.json"


def export_seed() -> int:
    """Write the current store's analyzed inspections, with original photos, to backend/seed/."""
    store._load_persisted_fallback()
    records = {key: record for key, record in store._MEMORY_INSPECTIONS.items() if record.get("analysis")}
    if SEED_DIR.exists():
        shutil.rmtree(SEED_DIR)
    (SEED_DIR / "images").mkdir(parents=True)
    seeded = {}
    for key, record in records.items():
        record = copy.deepcopy(record)
        for image in record.get("images", {}).values():
            source = Path(image["filepath"])
            shutil.copyfile(source, SEED_DIR / "images" / source.name)
            image["filepath"] = f"images/{source.name}"
            if image.get("preprocessing"):
                for path_key in ("filepath", "processed_filepath"):
                    image["preprocessing"].pop(path_key, None)
        record["database_saved"] = False
        record["mode"] = "Demo / Offline Fallback"
        record.pop("db_id", None)
        seeded[key] = record
    SEED_FILE.write_text(json.dumps(seeded, indent=1, ensure_ascii=False), encoding="utf-8")
    return len(seeded)


def install_seed() -> int:
    """Install the shipped inspections into an empty store; a store with any record is left alone."""
    if store._MEMORY_INSPECTIONS or not SEED_FILE.exists():
        return 0
    images_dir = Path(store.DATA_DIR) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    seeded = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    for record in seeded.values():
        for view, image in record.get("images", {}).items():
            raw = (SEED_DIR / image["filepath"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != image["file_hash"]:
                raise ValueError(f"Seed photo for {record['id']}/{view} does not match its recorded hash.")
            target = images_dir / Path(image["filepath"]).name
            target.write_bytes(raw)
            image["filepath"] = str(target)
            processed = preprocess_package_image(raw)
            if image.get("preprocessing") and processed.get("success"):
                processed_path = images_dir / f"{record['id']}_{view}_processed.jpg"
                processed_path.write_bytes(processed["processed_bytes"])
                image["preprocessing"].update(filepath=str(processed_path), processed_filepath=str(processed_path),
                                              file_hash=processed["processed_file_hash"])
            elif image.get("preprocessing"):
                image["preprocessing"] = None
        store._MEMORY_INSPECTIONS[record["id"]] = record
    store._save_persisted_fallback()
    return len(seeded)


if __name__ == "__main__":
    if sys.argv[1:] != ["export"]:
        sys.exit("usage: python -m app.services.seed export")
    print(f"Exported {export_seed()} inspections to {os.path.relpath(SEED_DIR)}")
