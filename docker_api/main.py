"""
WaveSign API — Private signing and verification service.
"""

import io
import json
import os
import zipfile

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from core import embed_watermark, sign_image, verify_image, detect_mode
from pdf_utils import sign_pdf, verify_pdf

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="WaveSign API", docs_url=None, redoc_url=None)

# API key loaded once at startup
_API_KEY: str = os.environ.get("WS_API_KEY", "")

# Routes that do not require authentication
_PUBLIC_ROUTES = {"/health", "/"}


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def require_api_key(request: Request, call_next):
    if request.url.path in _PUBLIC_ROUTES:
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "Missing or malformed Authorization header."},
        )
    token = auth_header[len("Bearer "):]
    if not _API_KEY or token != _API_KEY:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid API key."},
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_pdf(filename: str) -> bool:
    return filename.lower().endswith(".pdf")


def _build_zip(files: dict) -> io.BytesIO:
    """
    Build an in-memory ZIP archive.
    files: {archive_name: bytes}
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "service": "WaveSign API",
        "version": "1.0",
        "endpoints": {
            "POST /sign": "Sign an image or PDF. Params: file, key. Returns ZIP.",
            "POST /verify": "Verify a signed file. Params: file, sig_file, key. Returns JSON.",
            "GET /health": "Service health check.",
        },
        "auth": "Bearer token required for /sign and /verify.",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "WaveSign API"}


@app.post("/sign")
async def sign(
    file: UploadFile,
    key: str = Form(),
):
    try:
        raw = await file.read()
        filename = file.filename or "upload"

        if _is_pdf(filename):
            # PDF path
            signed_pdf_bytes, sigs, _ = sign_pdf(raw, secret=key)
            sig_json = json.dumps(sigs, indent=2).encode()
            archive = _build_zip({"signed.pdf": signed_pdf_bytes, "sig.json": sig_json})
        else:
            # Image path
            from PIL import Image
            img = Image.open(io.BytesIO(raw))
            mode = detect_mode(img)
            wm_img = embed_watermark(img, key, mode=mode)
            sig = sign_image(wm_img, key, mode=mode)

            out_buf = io.BytesIO()
            wm_img.save(out_buf, format="PNG")
            signed_png = out_buf.getvalue()

            sig_json = json.dumps(sig, indent=2).encode()
            archive = _build_zip({"signed.png": signed_png, "sig.json": sig_json})

        return StreamingResponse(
            archive,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="wavesign_output.zip"'},
        )

    except Exception as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.post("/verify")
async def verify(
    file: UploadFile,
    sig_file: UploadFile,
    key: str = Form(),
):
    try:
        raw = await file.read()
        sig_raw = await sig_file.read()
        filename = file.filename or "upload"

        sig_data = json.loads(sig_raw.decode())

        if _is_pdf(filename):
            # sig_data is a list of per-page signature dicts
            per_page = verify_pdf(raw, secret=key, signatures=sig_data)
            overall = all(p.get("is_valid", False) for p in per_page)
            verdict = "AUTHENTIC" if overall else "TAMPERED or INVALID KEY"

            # Normalise per-page entries to use consistent field names
            normalised = []
            for p in per_page:
                normalised.append({
                    "page_index": p.get("page_index"),
                    "is_valid": p.get("is_valid", False),
                    "verdict": "AUTHENTIC" if p.get("is_valid", False) else "TAMPERED or INVALID KEY",
                    "similarity_score": p.get("similarity_score"),
                    "mode": p.get("mode"),
                })

            return JSONResponse({
                "is_valid": overall,
                "verdict": verdict,
                "pages": normalised,
            })

        else:
            # Image path — sig_data is a single signature dict
            from PIL import Image
            img = Image.open(io.BytesIO(raw))
            result = verify_image(img, key, sig_data)
            is_valid = result.get("is_valid", False)
            return JSONResponse({
                "is_valid": is_valid,
                "verdict": "AUTHENTIC" if is_valid else "TAMPERED or INVALID KEY",
                "similarity_score": result.get("similarity_score"),
                "mode": result.get("mode"),
            })

    except Exception as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
