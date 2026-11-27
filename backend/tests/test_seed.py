"""The shipped sample inspections install into an empty store and serve like captured ones."""

import hashlib
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

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


def test_report_downloads_and_rejects_changed_evidence(empty_store):
    with TestClient(app) as client:
        record = next(r for r in client.get("/inspections/").json() if r["id"] == "INS-2026-579CF222")
        url = f"/inspections/{record['id']}/report"
        pdf = client.get(url, params={"format": "pdf"})
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.headers["content-disposition"].endswith('.pdf"')
        word = client.get(url, params={"format": "docx"})
        assert word.status_code == 200 and word.headers["content-disposition"].endswith('.docx"')
        with ZipFile(BytesIO(word.content)) as archive:
            document = archive.read("word/document.xml")
            assert record["id"].encode() in document
            assert b"07 AUG 2027" in document
            assert any(name.startswith("word/media/") for name in archive.namelist())
            assert record["analysis"]["views"]["rear"]["file_hash"].encode() in document
        Path(record["images"]["rear"]["filepath"]).write_bytes(b"changed")
        for format in ("html", "pdf", "docx"):
            assert client.get(url, params={"format": format}).status_code == 409


def test_seed_never_touches_a_store_with_records(empty_store):
    store._MEMORY_INSPECTIONS["INS-MINE"] = {"id": "INS-MINE"}
    assert install_seed() == 0
    assert list(store._MEMORY_INSPECTIONS) == ["INS-MINE"]


def test_mobile_creation_is_idempotent_after_restarting_the_store(empty_store):
    client = TestClient(app)
    payload = {"client_request_id": "fbba4b78-5193-4569-b485-b1e59df79980"}
    created = client.post("/inspections/", json=payload)
    assert created.status_code == 201
    store._MEMORY_INSPECTIONS = {}
    store._load_persisted_fallback()
    retried = client.post("/inspections/", json=payload)
    assert retried.status_code == 201
    assert retried.json() == created.json()
    assert len(client.get("/inspections/").json()) == 1
