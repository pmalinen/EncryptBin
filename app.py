
import os, json, time, uuid
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from storage import get_store

__version__ = "0.4.4"
ALLOW_PLAINTEXT = os.getenv("ENCRYPTBIN_ALLOW_PLAINTEXT", "false").lower() == "true"
MAX_PASTE_BYTES = int(os.getenv("ENCRYPTBIN_MAX_PASTE_BYTES", "10485760"))
EXP_CHOICES = {"1d": 86400, "1m": 2592000, "never": 0}

app = FastAPI(title="EncryptBin", version=__version__)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
store = get_store()

def generate_id() -> str:
    return uuid.uuid4().hex[:12]

def compute_expiry(created: int, choice: str) -> int:
    secs = EXP_CHOICES.get(choice, 0)
    return (created + secs) if secs > 0 else 0

def is_expired(meta: Dict[str, Any]) -> bool:
    exp = int(meta.get("expires", 0) or 0)
    return exp != 0 and int(time.time()) > exp

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "version": __version__})

@app.get("/api/version")
def api_version():
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
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    created = int(time.time())
    paste_id = generate_id()
    edit_key = uuid.uuid4().hex
    expires_choice = payload.get("expires", "never")
    burn_after = bool(payload.get("burnAfter", False))
    meta = {
        "title": str(payload.get("title", ""))[:140],
        "created": created,
        "expires": compute_expiry(created, expires_choice),
        "encrypted": True,
        "alg": alg,
        "burn_after": burn_after,
        "edit_key": edit_key,
    }
    await store.save(paste_id, json.dumps({
        "ciphertext_b64": ciphertext_b64,
        "iv_b64": iv_b64,
        "alg": alg
    }), meta)
    return {"url": f"/p/{paste_id}", "editKey": edit_key, "pasteId": paste_id}

if ALLOW_PLAINTEXT:
    @app.post("/api/paste", response_class=PlainTextResponse)
    async def paste_plain(request: Request):
        body = await request.body()
        if len(body) > MAX_PASTE_BYTES:
            raise HTTPException(status_code=413, detail="Paste too large")
        text = body.decode("utf-8", errors="replace")
        if not text.strip():
            raise HTTPException(status_code=400, detail="Empty paste")
        paste_id = generate_id()
        created = int(time.time())
        meta = {
            "title": "",
            "created": created,
            "expires": compute_expiry(created, "never"),
            "encrypted": False,
            "burn_after": False,
            "edit_key": uuid.uuid4().hex,
        }
        await store.save(paste_id, text, meta)
        return f"{paste_id}\n"
else:
    @app.post("/api/paste")
    async def paste_disabled():
        raise HTTPException(status_code=404, detail="Plaintext pastes are disabled. Set ENCRYPTBIN_ALLOW_PLAINTEXT=true to enable.")

@app.patch("/api/paste/{paste_id}")
async def update_title(paste_id: str, request: Request, authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing edit token")
    edit_key = authorization.split(" ", 1)[1]
    rec = await store.get(paste_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Not found")
    meta = rec.get("meta", {})
    if edit_key != meta.get("edit_key"):
        raise HTTPException(status_code=403, detail="Invalid edit token")
    try:
        body = await request.json()
        meta["title"] = str(body.get("title",""))[:140]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid body")
    await store.save(paste_id, rec["content"], meta)
    return {"ok": True, "title": meta["title"]}

@app.get("/p/{paste_id}", response_class=HTMLResponse)
async def view_paste(request: Request, paste_id: str):
    rec = await store.get(paste_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Not found")
    meta = rec.get("meta", {})
    if is_expired(meta):
        await store.delete(paste_id)
        raise HTTPException(status_code=404, detail="Not found")
    encrypted = bool(meta.get("encrypted", False))
    content = rec["content"]
    if meta.get("burn_after", False):
        await store.delete(paste_id)
    return templates.TemplateResponse("paste.html", {
        "request": request,
        "paste_id": paste_id,
        "title": meta.get("title",""),
        "created": meta.get("created",0),
        "expires": meta.get("expires",0),
        "encrypted": encrypted,
        "encrypted_payload": content if encrypted else "",
        "plaintext_payload": content if not encrypted else "",
        "meta": meta,
        "version": __version__,
    })

@app.get("/raw/{paste_id}", response_class=PlainTextResponse)
async def raw_paste(paste_id: str):
    rec = await store.get(paste_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Not found")
    meta = rec.get("meta", {})
    if is_expired(meta):
        await store.delete(paste_id)
        raise HTTPException(status_code=404, detail="Not found")
    if meta.get("encrypted", False):
        return PlainTextResponse("[encrypted]")
    return PlainTextResponse(rec["content"])
