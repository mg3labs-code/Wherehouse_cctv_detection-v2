"""Per-camera monitoring profiles — config-driven, not filename-driven.

This replaces the old ``video_profiles.py``, which recognized each of a
handful of known demo clips *by matching substrings in the video's
filename* (e.g. "godown no-3", "25076934") and returned a different,
hand-tuned block of constants for each one. That worked for exactly the
clips it was built and tested against, and nothing else — a brand-new
camera, a renamed file, or a live RTSP feed with no meaningful filename at
all would silently fall through with no recognizable identity.

The replacement here has one job: resolve a stable ``camera_id`` (chosen by
whoever is deploying the camera — an operator, or the API caller) against
an external, human-editable config file (``config/cameras.json``). Every
camera that has no entry in that file gets the same sane ``default``
profile, so a brand-new camera works immediately with zero setup. An
operator who wants to fine-tune a specific install (draw a danger zone,
change a proximity threshold) adds one small JSON block for that camera's
id — no Python changes, no redeploy.

If ``camera_id`` isn't given explicitly (e.g. an ad-hoc CLI run against a
local file), we fall back to using the file's name as the lookup key. That
is NOT filename pattern-matching — it's just treating the filename as the
camera's identity when nothing better was provided, and it still does a
single exact-key lookup rather than guessing from substrings.
"""
from __future__ import annotations

import copy
import json
import os
import threading
from typing import Any, Dict, Optional

DEFAULT_CAMERA_KEY = "default"

# Built-in fallback used only if config/cameras.json is missing or unreadable,
# so the system never crashes for lack of a config file.
_BUILTIN_DEFAULT: Dict[str, Any] = {
    "name": DEFAULT_CAMERA_KEY,
    "mode": "warehouse",
    "title": "Hypervis Warehouse Safety Monitor - AI Powered",
    "location": "Aisle",
    "enable_yellow_lines": True,
    "enable_forklift_lights": True,
    "enable_forklift_detect": True,
    "enable_ppe_dashboard": True,
    "proximity_px": 150,
    "danger_zone": None,
}

_lock = threading.Lock()
_cache: Dict[str, Any] = {"mtime": None, "data": None}


def _config_path() -> str:
    from .config import Config
    return getattr(
        Config,
        "CAMERA_CONFIG_PATH",
        os.path.join(Config.PROJECT_ROOT, "config", "cameras.json"),
    )


def _load_config() -> Dict[str, Any]:
    """Load config/cameras.json, cached and re-read whenever the file changes.

    This means an operator can edit the JSON file on a running deployment
    and have it picked up on the next camera start — no code deploy needed.
    """
    path = _config_path()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {"default": _BUILTIN_DEFAULT, "cameras": {}}

    with _lock:
        if _cache["mtime"] == mtime and _cache["data"] is not None:
            return _cache["data"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {"default": _BUILTIN_DEFAULT, "cameras": {}}
        data.setdefault("default", _BUILTIN_DEFAULT)
        data.setdefault("cameras", {})
        _cache["mtime"] = mtime
        _cache["data"] = data
        return data


def _derive_key(source: Any) -> str:
    """Fallback identity when no explicit camera_id is supplied."""
    if source is None or isinstance(source, int) or (isinstance(source, str) and source.isdigit()):
        return DEFAULT_CAMERA_KEY
    stem = os.path.splitext(os.path.basename(str(source)))[0].strip()
    return stem or DEFAULT_CAMERA_KEY


def resolve_profile(source: Any = None, camera_id: Optional[str] = None) -> Dict[str, Any]:
    """Return the profile dict for a camera.

    ``camera_id`` should be supplied explicitly by the caller whenever
    possible (e.g. from the API request, or a camera registry) — that is
    the correct, stable identity for a real deployment. ``source`` (a file
    path, RTSP URL, or webcam index) is only used as a same-value exact-key
    fallback when no camera_id is given, e.g. for quick local testing.
    """
    cfg = _load_config()
    key = camera_id.strip() if camera_id else _derive_key(source)

    profile = copy.deepcopy(cfg.get("default") or _BUILTIN_DEFAULT)
    override = cfg.get("cameras", {}).get(key)
    if isinstance(override, dict):
        profile.update(override)

    profile["camera_id"] = key
    profile.setdefault("name", key)
    return profile


def is_project16(profile: Optional[Dict[str, Any]]) -> bool:
    return bool(profile) and profile.get("mode") == "project16"


def is_safe_route(profile: Optional[Dict[str, Any]]) -> bool:
    return bool(profile) and profile.get("mode") == "safe_route"


def is_sawant_forklift(profile: Optional[Dict[str, Any]]) -> bool:
    return bool(profile) and profile.get("mode") == "sawant_forklift"
