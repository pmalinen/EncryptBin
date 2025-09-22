import json
import os
import time
import uuid
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from storage import get_store

__version__ = os.getenv("APP_VERSION", "0.4.4")

MAX_PASTE_BYTES = 1024 * 1024 * 2  # 2MB
store = get_store()
templates = Jinja2Templates(directory="templates")

app = FastAPI(title="EncryptBin")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


def generate_id():
    return uuid.uuid4().hex[:12]


def compute_expiry(created: int, choice: str) -> int:
    if choice == "never":
        return 0
    secs = 0
    if choice == "1d":
        secs = 86400
    elif choice == "30d":
        secs = 86400 * 30
    elif choice == "burn":
        secs = -1
    return (created + secs) if secs > 0 else 0


def expired(exp: int) -> bool:
    return exp != 0 and int(time.time()) > exp


@app.get("/")
async def index():
    return templates.TemplateResponse("index.html", {"request": {}})


@app.get("/api/version")
async def version():
    return {"version": __version__}


@app.post("/api/paste_encrypted")
async def paste_encrypted(request: Request):
    body = await request.body()
    if len(body) > MAX_PASTE_BYTES:
        raise HTTPException(status_code=413, detail="Paste too large")
    try:
        payload = json.loads(body.decode("utf-8"))
        ciphertext_b64 = payload["ciphertext_b64"]
        iv_b64 = payload["iv_b64"]
        alg = payload.get("alg", "AES-GCM")
        title = payload.get("title", "")
        expires_choice = payload.get("expires", "never")
        burn_after = bool(payload.get("burn_after"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    paste_id = generate_id()
    edit_key = uuid.uuid4().hex
    created = int(time.time())
    meta = {
        "title": title,
        "created": created,
        "expires": compute_expiry(created, expires_choice),
        "encrypted": True,
        "burn_after": burn_after,
        "alg": alg,
        "edit_key": edit_key,
    }
    try:
        await store.save_encrypted(paste_id, ciphertext_b64, iv_b64, alg, meta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving paste: {e}")

    base_url = str(request.base_url).rstrip("/")
    return JSONResponse(
        {
            "id": paste_id,
            "url": f"{base_url}/p/{paste_id}",
            "raw_url": f"{base_url}/raw/{paste_id}",
            "edit_key": edit_key,
        }
    )


# Enabled only if ENCRYPTBIN_ALLOW_PLAINTEXT=true
if os.getenv("ENCRYPTBIN_ALLOW_PLAINTEXT", "false").lower() == "true":

    @app.post("/api/paste")
    async def paste_plain(request: Request):
        body = await request.body()
        if len(body) > MAX_PASTE_BYTES:
            raise HTTPException(status_code=413, detail="Paste too large")
        text = body.decode("utf-8", errors="replace")
        if not text.strip():
            raise HTTPException(status_code=400, detail="Empty paste")

        paste_id = generate_id()
        edit_key = uuid.uuid4().hex
        created = int(time.time())
        meta = {
            "title": "",
            "created": created,
            "expires": compute_expiry(created, "never"),
            "encrypted": False,
            "burn_after": False,
            "edit_key": edit_key,
        }
        try:
            await store.save(paste_id, text, meta)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving paste: {e}")

        base_url = str(request.base_url).rstrip("/")
        return JSONResponse(
            {
                "id": paste_id,
                "url": f"{base_url}/p/{paste_id}",
                "raw_url": f"{base_url}/raw/{paste_id}",
                "edit_key": edit_key,
            }
        )

else:

    @app.post("/api/paste")
    async def paste_disabled():
        raise HTTPException(
            status_code=404,
            detail=(
                "Plaintext pastes are disabled. "
                "Set ENCRYPTBIN_ALLOW_PLAINTEXT=true to enable."
            ),
        )


@app.patch("/api/paste/{paste_id}")
async def update_title(
    paste_id: str, request: Request, authorization: Optional[str] = Header(default=None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Missing or invalid token")
    token = authorization.split(" ")[1]
    allowed = os.getenv("API_TOKENS", "").split(",")
    if token not in allowed:
        raise HTTPException(status_code=403, detail="Unauthorized")
    body = await request.json()
    title = body.get("title", "")
    rec = await store.get(paste_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Paste not found")
    rec["meta"]["title"] = title
    await store.put(paste_id, rec)
    return {"ok": True, "title": title}


@app.get("/p/{paste_id}")
async def view_paste(paste_id: str, request: Request):
    rec = await store.get(paste_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Paste not found")
    meta = rec["meta"]
    if expired(meta["expires"]):
        raise HTTPException(status_code=404, detail="Paste expired")

    encrypted_payload = None
    plaintext_payload = ""

    if meta.get("encrypted"):
        encrypted_payload = rec.get("encrypted_payload", {})
    else:
        plaintext_payload = rec.get("content", "")

    return templates.TemplateResponse(
        "paste.html",
        {
            "request": request,
            "paste_id": paste_id,
            "meta": meta,
            "expires": meta.get("expires", 0),
            "encrypted_payload": encrypted_payload,
            "plaintext_payload": plaintext_payload,
            "version": __version__,
        },
    )


@app.get("/raw/{paste_id}")
async def raw_paste(paste_id: str):
    rec = await store.get(paste_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Paste not found")
    meta = rec["meta"]
    if expired(meta["expires"]):
        raise HTTPException(status_code=404, detail="Paste expired")
    if meta.get("encrypted"):
        return PlainTextResponse("[encrypted]")
    return PlainTextResponse(rec["content"])
