# Phase 0 + Phase 2 changes (this repo is a separate copy — see note at bottom)

This document explains, file by file, what changed here versus the original
`Wherehouse_cctv_detection` repo, why, and what you need to configure before
deploying it. It corresponds to Phase 0 (API security lockdown) and Phase 2
(replace the per-clip `video_profiles.py` hacks with a generalized,
camera-agnostic danger-zone check) from the earlier review report.

## Phase 0 — API security lockdown

**Before:** `src/api/app.py` set `allow_origins=["*"]` (any website could call
this API from a visitor's browser) and had no authentication at all — anyone
who found the Railway URL could upload videos, delete videos, or start/stop
the live camera feed.

**After:**

- Every request under `/api/*` (except `/api/health`, explained below) now
  requires a shared-secret key, sent as the `X-API-Key` header or an
  `api_key` query parameter. See the new `_require_api_key` middleware in
  `src/api/app.py`. The key comes from the `HYPERVIS_API_KEY` environment
  variable (`src/config.py`) — with it unset, the server refuses every
  request rather than silently running wide open (fail closed, not fail
  open).
- `/api/health` stays reachable with no key. This is deliberate, not an
  oversight: Railway's own health-check prober (`railway.toml`) hits this
  path with no custom headers, and if it required a key the platform would
  think the service was unhealthy and restart it in a loop.
- Anything that isn't under `/api/` (the compiled dashboard's HTML/JS/CSS,
  served as static files when `frontend/dist` exists) also stays open,
  because a plain browser page load can't attach a custom header either.
  The page's own JS is what then calls `/api/*` with the key attached.
- CORS (`allow_origins`) now comes from `HYPERVIS_ALLOWED_ORIGINS`, a
  comma-separated list of exact origins, defaulting to localhost-only if
  unset. **You must set this to your real deployed frontend URL before this
  is useful in production** — see `.env.example`.

**Honest limitation, worth reading before you consider this "solved":** this
is a shared secret baked into a public single-page app's JS bundle at build
time. It stops a bot or a random visitor from hitting the API directly, but
anyone who deliberately opens browser devtools on the dashboard can read the
key out of the built JS. That is a real, useful improvement over "wide open
to the entire internet with no key at all," but it is not per-user
authentication. If this ever needs to distinguish between different human
users (rather than just "someone with the dashboard's URL"), that's a bigger
piece of work — real accounts/login — and should be scoped separately.

**What you need to do to deploy this:**

1. Generate a key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Backend: set `HYPERVIS_API_KEY` and `HYPERVIS_ALLOWED_ORIGINS` as real
   environment variables in Railway's Variables tab (see `.env.example`).
3. Frontend: set `VITE_API_KEY` to the *same* key as a real environment
   variable in the frontend's Railway service before it builds (see the
   frontend repo's `.env.example` / `.env.production`).

## Phase 2 — replace the filename-matching hacks with a generalized check

**Before:** `src/video_profiles.py` recognized exactly seven known demo
video clips by matching substrings in the filename (`"godown no-3"`,
`"25076934"`, `"sawant"`, etc.) and returned a different hand-tuned block of
detector-tuning constants for each one — built and refined, per the git
history, by watching each specific clip and adjusting numbers until it
looked right on screen. Anything that wasn't one of those seven clips fell
through to a generic default. There was also, on inspection of the actual
(non-dead-code) detection pipeline, **no forklift <-> person proximity check
at all** — the only proximity check that existed (`_check_conveyor_safety`)
checks distance to a "conveyor" class that the system has no trained ability
to ever detect, so it never fires in practice.

**After:**

- `src/video_profiles.py` is deleted. `src/camera_profiles.py` replaces it.
- Camera identity is now an explicit `camera_id` you choose (e.g.
  `"loading_dock_1"`), looked up as an **exact key** in `config/cameras.json`
  — not a fuzzy substring match against known filenames. Any camera_id (or
  filename, when no camera_id is given) that isn't in that file gets the
  same `"default"` profile, which is what makes a brand-new camera work
  immediately with zero setup.
- `config/cameras.json` is a plain, human-editable file, re-read
  automatically whenever it changes (no code deploy needed) — see the
  comments inside it for how to add a real camera.
- `src/danger_zone.py` is new: a proximity/danger-zone checker that (1)
  always flags a person whose position is within a configurable pixel
  distance of a detected forklift — this requires zero per-camera setup and
  is what makes the check camera-agnostic — and (2), only if an operator has
  drawn a `danger_zone` polygon for that specific camera in
  `config/cameras.json`, also flags anyone standing inside that polygon
  while a forklift is active in frame. It's wired into the main detection
  loop in `src/monitor.py` (`process_frame`), emitting `PERSON_NEAR_FORKLIFT`
  / `PERSON_IN_DANGER_ZONE` violations that flow into the same
  logging/analytics pipeline as every other violation type, and into the
  on-screen alert banner with the highest priority (a person near a moving
  forklift is a more acute hazard than a missing helmet).
- The existing "Video Project 16" mode (a distinct, working feature for
  detecting hand contact with raw product on a production line — this is a
  different thing entirely from the forklift-aisle hacks, and was left
  alone) and the forklift-detection tuning machinery (merging duplicate
  boxes, motion gating, yellow-blob fallback, etc.) are untouched. Phase 2
  was scoped to the filename-matching architecture and the missing
  proximity check specifically, not a rewrite of the detector itself — that
  tuning work is still real, still somewhat hand-fit, and is exactly what
  Phase 1 (training a real PPE/forklift model on real data) in the original
  report is meant to address.

**What this means practically:** because the seven demo clips no longer get
their individually hand-tuned constants, they may show more false positives
or missed detections than the original repo's carefully-fitted version when
you play them back. That's expected and is the actual tradeoff being made —
uniform, camera-agnostic defaults instead of per-clip perfection — and it's
exactly what makes this version able to run on a camera nobody has tuned for
yet, which the original could not do.

**To configure a real camera:** open `config/cameras.json`, copy the example
block under `"cameras"`, rename its key to the `camera_id` you'll pass to
`POST /api/live/start` (or `--camera-id` on the CLI), and adjust
`proximity_px` and/or draw a `danger_zone` polygon (normalized 0..1 points,
clockwise). No code changes, no redeploy.

## Tests

`tests/` is new (there wasn't one before, despite being listed in the
original README's project structure diagram). Run with:

```
pip install -r requirements-dev.txt
pytest tests/ -v
```

`test_danger_zone.py` and `test_camera_profiles.py` are pure logic tests, no
dependencies beyond the standard library. `test_api_security.py` exercises
the real FastAPI app (auth, CORS, the fail-closed behavior) with `ultralytics`
stubbed out, since none of that needs an actual model loaded to verify. All
23 tests pass as of this change.

## About this repo

This is a full copy of the original, including its git history, kept
completely separate so the original `mg3labs-code/Wherehouse_cctv_detection`
repo is untouched and the two can be compared directly (e.g.
`git diff <original-repo>/main..HEAD` if you add it as a second remote, or
just diff the two checkouts). See the matching frontend repo,
`Wherehouse_cctv_detection_frontend-v2`, for the corresponding frontend
changes (mainly: sending the API key on every request).
