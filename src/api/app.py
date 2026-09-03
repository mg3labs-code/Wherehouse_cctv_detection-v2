"""GLS Warehouse Safety — FastAPI backend."""
from __future__ import annotations

import glob
import hmac
import os
import re
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..config import Config
from . import store
from .live import live_service

app = FastAPI(
    title="Hypervis Warehouse Safety API",
    version="1.0.0",
    description="Production API for Hypervis warehouse safety analytics and live monitoring",
)

app.add_middleware(
    CORSMiddleware,
    # Explicit, known origins only — see HYPERVIS_ALLOWED_ORIGINS in config.py.
    # "*" is no longer used: it let any website on the internet call this API
    # from a visitor's browser.
    allow_origins=Config.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API key authentication -------------------------------------------------
# Every /api/* endpoint requires a shared-secret key, sent as either the
# X-API-Key header or an api_key query parameter (the query param exists only
# because the browser's <img>/<video> tags can't set custom headers; this
# frontend doesn't currently rely on that path — see the frontend's api/client.ts).
#
# Two paths are always public, deliberately:
#   - /api/health: Railway's own health-check prober hits this with no
#     headers at all. If this required a key, the platform would think the
#     service was down and restart it in a loop.
#   - Anything NOT under /api/: this is the built-in static-file server for
#     the compiled dashboard (frontend/dist). A browser's plain page
#     navigation can't send a custom header either, so the page shell itself
#     has to stay reachable — its own JS is what then calls /api/* with the
#     key attached.
#
# NOTE (please read before treating this as done): baking a shared key into a
# public single-page app's JS bundle deters casual scraping/abuse of a public
# URL, which is the gap this closes — but the key is visible to anyone who
# opens browser devtools on the dashboard. It is not per-user authentication.
# Real user accounts/login are a bigger piece of work than "Phase 0" scope
# and should follow if/when this handles real customer data.
_PUBLIC_PATHS = {"/api/health"}
_API_KEY_HEADER = "x-api-key"


@app.middleware("http")
async def _require_api_key(request: Request, call_next):
    path = request.url.path
    if request.method == "OPTIONS" or not path.startswith("/api/") or path in _PUBLIC_PATHS:
        return await call_next(request)

    expected = Config.API_KEY
    if not expected:
        # Fail closed. A misconfigured deployment should refuse traffic, not
        # silently fall back to the old "wide open to the internet" behavior.
        return JSONResponse(
            {"detail": "Server misconfigured: HYPERVIS_API_KEY is not set."},
            status_code=500,
        )

    provided = request.headers.get(_API_KEY_HEADER) or request.query_params.get("api_key") or ""
    if not hmac.compare_digest(provided, expected):
        return JSONResponse({"detail": "Unauthorized: missing or invalid API key."}, status_code=401)

    return await call_next(request)


class StartLiveBody(BaseModel):
    source: str
    # Stable camera identity looked up in config/cameras.json (see
    # camera_profiles.py). Optional — omit it for ad-hoc local testing and
    # the source filename is used as a one-off exact-match lookup key instead.
    camera_id: Optional[str] = None


@app.on_event("startup")
def on_startup():
    store.init_db()
    # Real-time only — drop demo seeds and collapse per-frame alert spam
    store.purge_demo_events()
    store.consolidate_burst_duplicates()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "gls-warehouse-safety",
        "live": live_service.status().get("status"),
    }


@app.get("/api/worksites")
def get_worksites():
    return {"worksites": store.worksites()}


@app.get("/api/analytics/summary")
def analytics_summary(
    worksite: Optional[str] = Query(None),
    day: Optional[str] = Query(None, description="YYYY-MM-DD"),
    category: Optional[str] = Query(None, description="all|assets|operators|alerts"),
    scope: Optional[str] = Query(None, description="Secondary filter scope"),
):
    ws = None if not worksite or worksite in ("all", "--All Worksites--") else worksite
    return store.summary_kpis(ws, day=day, category=category, scope=scope)


@app.get("/api/analytics/timeseries")
def analytics_timeseries(
    days: int = Query(14, ge=7, le=90),
    worksite: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
):
    ws = None if not worksite or worksite in ("all", "--All Worksites--") else worksite
    return {
        "series": store.timeseries(
            days=days, worksite=ws, category=category, scope=scope
        )
    }


@app.get("/api/violations")
def get_violations(
    limit: int = Query(50, ge=1, le=5000),
    worksite: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    since_hours: Optional[int] = Query(None, ge=1, le=24 * 366),
):
    ws = None if not worksite or worksite in ("all", "--All Worksites--") else worksite
    return {
        "items": store.list_events(
            limit=limit,
            worksite=ws,
            event_type=event_type,
            since_hours=since_hours,
        )
    }


_VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov"}


def _video_dir() -> str:
    path = os.path.join(Config.DATA_DIR, "videos")
    os.makedirs(path, exist_ok=True)
    return path


def _list_video_items() -> list[dict]:
    video_dir = _video_dir()
    files: list[str] = []
    for ext in ("*.mp4", "*.MP4", "*.avi", "*.mkv", "*.mov"):
        files.extend(glob.glob(os.path.join(video_dir, ext)))
    files = sorted(set(files))
    items = []
    for i, path in enumerate(files, 1):
        items.append({
            "id": i,
            "name": os.path.basename(path),
            "path": os.path.relpath(path, Config.PROJECT_ROOT).replace("\\", "/"),
            "size_mb": round(os.path.getsize(path) / (1024 * 1024), 1),
        })
    return items


@app.get("/api/videos")
def list_videos():
    return {"items": _list_video_items()}


@app.post("/api/videos/upload")
async def upload_video(file: UploadFile = File(...)):
    """Save a CCTV clip into data/videos so Live Monitor can select it."""
    raw_name = os.path.basename(file.filename or "")
    if not raw_name:
        raise HTTPException(status_code=400, detail="Missing filename")
    ext = os.path.splitext(raw_name)[1].lower()
    if ext not in _VIDEO_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported type {ext or '(none)'}. Use: {', '.join(sorted(_VIDEO_EXTS))}",
        )
    safe = re.sub(r"[^\w.\- ]+", "_", raw_name).strip(" ._") or f"upload{ext}"
    if not safe.lower().endswith(ext):
        safe += ext
    dest = os.path.join(_video_dir(), safe)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    # Soft limit ~500 MB — Railway disks are finite
    if len(data) > 500 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 500 MB)")
    with open(dest, "wb") as f:
        f.write(data)
    rel = os.path.relpath(dest, Config.PROJECT_ROOT).replace("\\", "/")
    return {
        "ok": True,
        "item": {
            "id": 0,
            "name": os.path.basename(dest),
            "path": rel,
            "size_mb": round(len(data) / (1024 * 1024), 1),
        },
        "items": _list_video_items(),
    }


@app.delete("/api/videos")
def delete_video(name: str = Query(..., description="Basename of file inside data/videos")):
    """Remove a CCTV clip from data/videos (basename only; no path traversal)."""
    base = os.path.basename(name.strip().replace("\\", "/"))
    if not base or base in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid name")
    ext = os.path.splitext(base)[1].lower()
    if ext not in _VIDEO_EXTS:
        raise HTTPException(status_code=400, detail="Not a supported video file")
    video_dir = os.path.realpath(_video_dir())
    dest = os.path.realpath(os.path.join(video_dir, base))
    if dest != video_dir and not dest.startswith(video_dir + os.sep):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.isfile(dest):
        raise HTTPException(status_code=404, detail=f"Video not found: {base}")
    os.remove(dest)
    return {"ok": True, "deleted": base, "items": _list_video_items()}


def _resolve_video_file(name: str) -> str:
    base = os.path.basename(name.strip().replace("\\", "/"))
    if not base or base in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid name")
    ext = os.path.splitext(base)[1].lower()
    if ext not in _VIDEO_EXTS:
        raise HTTPException(status_code=400, detail="Not a supported video file")
    video_dir = os.path.realpath(_video_dir())
    dest = os.path.realpath(os.path.join(video_dir, base))
    if dest != video_dir and not dest.startswith(video_dir + os.sep):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not os.path.isfile(dest):
        raise HTTPException(status_code=404, detail=f"Video not found: {base}")
    return dest


_VIDEO_MEDIA = {
    ".mp4": "video/mp4",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
}


@app.get("/api/videos/file")
def get_video_file(name: str = Query(..., description="Basename of file inside data/videos")):
    """Stream a stored CCTV clip for in-browser playback."""
    dest = _resolve_video_file(name)
    ext = os.path.splitext(dest)[1].lower()
    media = _VIDEO_MEDIA.get(ext, "application/octet-stream")
    return FileResponse(dest, media_type=media, filename=os.path.basename(dest))


@app.get("/api/live/status")
def live_status():
    return live_service.status()

@app.post("/api/live/start")
def live_start(body: StartLiveBody):
    try:
        return live_service.start(body.source, camera_id=body.camera_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/live/stop")
def live_stop():
    return live_service.stop()


@app.get("/api/live/frame.jpg")
def live_frame():
    """Single latest JPEG — reliable for browsers that break on MJPEG."""
    import numpy as np
    import cv2

    jpeg = live_service.latest_jpeg()
    if not jpeg:
        blank = np.zeros((360, 640, 3), dtype=np.uint8)
        cv2.putText(
            blank, "Waiting for live feed...", (80, 180),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2,
        )
        ok, buf = cv2.imencode(".jpg", blank)
        jpeg = buf.tobytes() if ok else b""
    return Response(
        content=jpeg,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@app.get("/api/live/stream")
def live_stream():
    """MJPEG multipart stream of annotated frames."""

    def gen():
        import time
        last = None
        while True:
            jpeg = live_service.latest_jpeg()
            if not jpeg:
                import numpy as np
                import cv2
                blank = np.zeros((360, 640, 3), dtype=np.uint8)
                cv2.putText(
                    blank, "Waiting for live feed...", (80, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2,
                )
                ok, buf = cv2.imencode(".jpg", blank)
                jpeg = buf.tobytes() if ok else None
            if jpeg and jpeg is not last:
                last = jpeg
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n"
                    b"\r\n" + jpeg + b"\r\n"
                )
            time.sleep(0.08)

    return StreamingResponse(
        gen(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store", "Connection": "close"},
    )


# Optional: serve built frontend from frontend/dist when present
_DIST = os.path.join(Config.PROJECT_ROOT, "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/")
    def spa_index():
        return FileResponse(os.path.join(_DIST, "index.html"))

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not found")
        index = os.path.join(_DIST, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Frontend not built")
