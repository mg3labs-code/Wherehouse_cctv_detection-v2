"""Tests for the config-driven camera profile resolver.

The key property under test: a camera/video that has NO entry in
config/cameras.json still gets a complete, working profile (the
"default" block) — that's what makes a brand-new camera work without any
per-camera code. A camera WITH an entry gets the default merged with its
overrides. Nothing here is matched by filename substring guessing.
"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import src.camera_profiles as camera_profiles  # noqa: E402


def _reset_cache():
    camera_profiles._cache["mtime"] = None
    camera_profiles._cache["data"] = None


def _write_config(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def test_unknown_camera_gets_default_profile(tmp_path, monkeypatch):
    cfg_path = tmp_path / "cameras.json"
    _write_config(cfg_path, {
        "default": {"name": "default", "mode": "warehouse", "proximity_px": 150},
        "cameras": {},
    })
    monkeypatch.setattr(camera_profiles, "_config_path", lambda: str(cfg_path))
    _reset_cache()

    profile = camera_profiles.resolve_profile(source="some_brand_new_camera_nobody_configured.mp4")
    assert profile["mode"] == "warehouse"
    assert profile["proximity_px"] == 150
    assert profile["camera_id"] == "some_brand_new_camera_nobody_configured"


def test_explicit_camera_id_overrides_filename_derivation(tmp_path, monkeypatch):
    cfg_path = tmp_path / "cameras.json"
    _write_config(cfg_path, {
        "default": {"name": "default", "proximity_px": 150},
        "cameras": {
            "loading_dock_1": {"location": "Loading Dock 1", "proximity_px": 200},
        },
    })
    monkeypatch.setattr(camera_profiles, "_config_path", lambda: str(cfg_path))
    _reset_cache()

    # Even though the source filename doesn't match "loading_dock_1" at all,
    # an explicit camera_id is an exact-key lookup and wins.
    profile = camera_profiles.resolve_profile(
        source="unrelated_filename.mp4", camera_id="loading_dock_1"
    )
    assert profile["proximity_px"] == 200
    assert profile["location"] == "Loading Dock 1"
    assert profile["camera_id"] == "loading_dock_1"


def test_no_substring_matching_against_known_demo_names(tmp_path, monkeypatch):
    """A file that merely CONTAINS a configured camera's name as a substring
    must NOT match it — only an exact key match should, unlike the old
    video_profiles.py behavior this replaces."""
    cfg_path = tmp_path / "cameras.json"
    _write_config(cfg_path, {
        "default": {"name": "default", "proximity_px": 150},
        "cameras": {
            "godown_no3": {"proximity_px": 999},
        },
    })
    monkeypatch.setattr(camera_profiles, "_config_path", lambda: str(cfg_path))
    _reset_cache()

    # Old behavior would have matched "godown no-3" as a substring anywhere
    # in the filename. New behavior requires the exact stem to match.
    profile = camera_profiles.resolve_profile(
        source="ITC CHIRALA-CGLT_GODOWN NO-3 CAM-2_20260722182656_250.mp4"
    )
    assert profile["proximity_px"] == 150  # falls back to default, not 999


def test_missing_config_file_falls_back_to_builtin_default(tmp_path, monkeypatch):
    monkeypatch.setattr(
        camera_profiles, "_config_path", lambda: str(tmp_path / "does_not_exist.json")
    )
    _reset_cache()
    profile = camera_profiles.resolve_profile()
    assert profile["mode"] == "warehouse"
    assert profile["camera_id"] == "default"


def test_config_is_reloaded_after_file_changes(tmp_path, monkeypatch):
    cfg_path = tmp_path / "cameras.json"
    _write_config(cfg_path, {"default": {"proximity_px": 150}, "cameras": {}})
    monkeypatch.setattr(camera_profiles, "_config_path", lambda: str(cfg_path))
    _reset_cache()

    first = camera_profiles.resolve_profile()
    assert first["proximity_px"] == 150

    # Simulate an operator editing the JSON file live (no redeploy).
    import time
    time.sleep(0.01)
    _write_config(cfg_path, {"default": {"proximity_px": 175}, "cameras": {}})
    os.utime(cfg_path, None)

    second = camera_profiles.resolve_profile()
    assert second["proximity_px"] == 175
