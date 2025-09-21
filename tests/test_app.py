import os
import sys
import time

from fastapi.testclient import TestClient

from app import app

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


client = TestClient(app)


def test_create_and_retrieve_paste(tmp_path, monkeypatch):
    """Ensure a paste can be created and retrieved (raw)."""
    # Force local storage for tests
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    # Create a paste
    resp = client.post("/paste", data={"content": "hello world", "title": "Test"})
    assert resp.status_code == 200
    data = resp.json()
    assert "url" in data
    paste_url = data["url"]

    # Retrieve paste (raw)
    raw_url = paste_url.replace("/paste/", "/raw/")
    resp2 = client.get(raw_url)
    assert resp2.status_code == 200
    assert "hello world" in resp2.text


def test_expiration_and_cleanup(tmp_path, monkeypatch):
    """Expired pastes should be removed by cleanup."""
    import storage
    from cleanup import cleanup_expired

    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    # Create paste with expiration
    resp = client.post("/paste", data={"content": "temp", "expire": "1d"})
    assert resp.status_code == 200
    paste_id = resp.json()["id"]

    # Force expiry by manipulating metadata
    meta = storage.get_store().get_meta(paste_id)
    meta["expires"] = time.time() - 1
    storage.get_store().save_meta(paste_id, meta)

    # Run cleanup
    cleanup_expired(storage.get_store())

    # Paste should now be gone
    resp2 = client.get(f"/raw/{paste_id}")
    assert resp2.status_code == 404


def test_burn_after_read(tmp_path, monkeypatch):
    """Pastes marked burn-after-read should be deleted after the first view."""
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    # Create paste with burn_after=1
    resp = client.post("/paste", data={"content": "secret", "burn_after": "1"})
    assert resp.status_code == 200
    paste_id = resp.json()["id"]

    # First read should succeed
    resp2 = client.get(f"/raw/{paste_id}")
    assert resp2.status_code == 200
    assert "secret" in resp2.text

    # Second read should fail
    resp3 = client.get(f"/raw/{paste_id}")
    assert resp3.status_code == 404
