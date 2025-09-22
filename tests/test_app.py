# flake8: noqa: E402
import os
import sys

# Ensure repo root is on sys.path *before* importing app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import base64
import json
import secrets

import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_version_endpoint():
    resp = client.get("/api/version")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data


@pytest.mark.parametrize("content", ["hello world", "another paste"])
def test_plaintext_paste_and_retrieve(content):
    # This only works if ENCRYPTBIN_ALLOW_PLAINTEXT=true
    resp = client.post("/api/paste", data=content.encode("utf-8"))
    if resp.status_code == 404:
        pytest.skip("Plaintext pastes disabled")
    assert resp.status_code == 200
    paste_id = resp.text.strip()

    # Retrieve raw
    raw = client.get(f"/raw/{paste_id}")
    assert raw.status_code == 200
    assert content in raw.text


def test_encrypted_paste_roundtrip():
    # Generate fake iv and ciphertext
    iv = secrets.token_bytes(12)
    ciphertext = base64.b64encode(b"dummycipher").decode("utf-8")
    iv_b64 = base64.b64encode(iv).decode("utf-8")

    payload = {
        "ciphertext_b64": ciphertext,
        "iv_b64": iv_b64,
        "alg": "AES-GCM",
        "title": "test",
        "expires": "1d",
        "burn_after": False,
    }
    resp = client.post("/api/paste_encrypted", data=json.dumps(payload))
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "url" in data
