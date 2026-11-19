"""The shipped sample inspections install into an empty store and serve like captured ones."""

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import inspection_store as store
from app.services.seed import SEED_FILE, install_seed


@pytest.fixture
def empty_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "FALLBACK_FILE", str(tmp_path / "inspections.json"))
    monkeypatch.setattr(store, "_MEMORY_INSPECTIONS", {})
    monkeypatch.setattr(store, "is_database_available", lambda: False)
    return tmp_path


@pytest.mark.skipif(not SEED_FILE.exists(), reason="no seed shipped")
def test_seed_installs_on_first_start_with_original_photos_and_rebuilt_copies(empty_store):
    with TestClient(app) as client:  # the lifespan installs the seed
        records = client.get("/inspections/").json()
        assert len(records) == 7 and all(r["analysis"] for r in records)
        assert (empty_store / "inspections.json").exists()
        for record in records:
            for view, image in record["images"].items():
                assert hashlib.sha256(Path(image["filepath"]).read_bytes()).hexdigest() == image["file_hash"]
                assert record["analysis"]["views"][view]["file_hash"] == image["file_hash"]
                assert client.get(f"/inspections/{record['id']}/images/{view}/processed").status_code == 200
        potata = next(r for r in records if r["id"] == "INS-2026-579CF222")
        fields = {f["field"]: f["value"] for f in potata["analysis"]["fields"]}
        assert fields["date"] == "08 AUG 2026" and fields["expiry"] == "07 AUG 2027"
        assert client.get(f"/inspections/{potata['id']}/report").status_code == 200


def test_seed_never_touches_a_store_with_records(empty_store):
    store._MEMORY_INSPECTIONS["INS-MINE"] = {"id": "INS-MINE"}
    assert install_seed() == 0
    assert list(store._MEMORY_INSPECTIONS) == ["INS-MINE"]
