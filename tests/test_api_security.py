"""Tests for Phase 0: every /api/* endpoint requires an API key, CORS is
locked to explicit origins, and /api/health stays reachable for platform
health checks.

The real ComplianceMonitor pulls in ultralytics/torch, which this test
environment doesn't need installed just to prove the auth/CORS layer works
correctly — so ultralytics is stubbed out before the app is imported. That
stub is never exercised: these tests never actually start a detector.
"""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _install_ultralytics_stub():
    if "ultralytics" in sys.modules:
        return

    class _FakeYOLO:
        def __init__(self, *a, **k):
            pass

        def __call__(self, *a, **k):
            raise RuntimeError("stub YOLO should never actually be invoked in these tests")

    stub = types.ModuleType("ultralytics")
    stub.YOLO = _FakeYOLO
    sys.modules["ultralytics"] = stub


_install_ultralytics_stub()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

os.environ["HYPERVIS_API_KEY"] = "test-secret-key"
os.environ["HYPERVIS_ALLOWED_ORIGINS"] = "https://dashboard.example.com"

import importlib  # noqa: E402

# src/api/__init__.py does `from .app import app`, which rebinds the `app`
# attribute on the `src.api` package to the FastAPI *instance* — so
# `import src.api.app as x` (or `from src.api import app as x`) hands you
# that instance, not the submodule, because both forms resolve via
# attribute-chain traversal rather than a sys.modules lookup.
# importlib.import_module() returns the actual submodule from sys.modules,
# sidestepping the shadowed attribute, so we get both `.app` (the FastAPI
# instance) and `.Config` off of it.
app_module = importlib.import_module("src.api.app")


@pytest.fixture(scope="module")
def client():
    # Used as a context manager so FastAPI's startup event (store.init_db())
    # runs before any request hits the app — /api/violations needs the DB.
    with TestClient(app_module.app) as c:
        yield c


def test_health_is_reachable_without_any_api_key(client):
    """Railway's health checker sends no headers at all — this must stay open."""
    r = client.get("/api/health")
    assert r.status_code == 200


def test_protected_endpoint_rejects_missing_key(client):
    r = client.get("/api/violations")
    assert r.status_code == 401


def test_protected_endpoint_rejects_wrong_key(client):
    r = client.get("/api/violations", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_protected_endpoint_accepts_correct_header_key(client):
    r = client.get("/api/violations", headers={"X-API-Key": "test-secret-key"})
    assert r.status_code == 200


def test_protected_endpoint_accepts_correct_query_param_key(client):
    # Only relevant for the rare case of a plain <img>/<video> src that can't
    # set headers — the frontend's fetch-based client uses the header path.
    r = client.get("/api/violations?api_key=test-secret-key")
    assert r.status_code == 200


def test_mutating_endpoints_are_also_protected(client):
    r = client.post("/api/live/stop")
    assert r.status_code == 401

    r = client.delete("/api/videos", params={"name": "whatever.mp4"})
    assert r.status_code == 401


def test_cors_reflects_only_configured_origin(client):
    allowed = client.get(
        "/api/health",
        headers={"Origin": "https://dashboard.example.com"},
    )
    assert allowed.headers.get("access-control-allow-origin") == "https://dashboard.example.com"

    blocked = client.get(
        "/api/health",
        headers={"Origin": "https://some-random-site.example"},
    )
    # Starlette's CORS middleware simply omits the header for a disallowed
    # origin rather than returning an error status.
    assert "access-control-allow-origin" not in blocked.headers


def test_server_fails_closed_when_no_api_key_configured(client, monkeypatch):
    monkeypatch.setattr(app_module.Config, "API_KEY", "")
    r = client.get("/api/violations", headers={"X-API-Key": "anything"})
    assert r.status_code == 500
