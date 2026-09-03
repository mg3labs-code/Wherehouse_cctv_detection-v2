"""Tests for the generalized, camera-agnostic proximity/danger-zone check.

These exercise pure geometry/logic against synthetic bounding boxes — no
YOLO model, no video file, no per-clip anything. That's the point: this
check has to work the same way regardless of which camera the boxes came
from.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.danger_zone import (  # noqa: E402
    DEFAULT_PROXIMITY_PX,
    DangerZoneChecker,
    bbox_center,
    point_in_polygon,
    polygon_to_pixels,
)


def _person(x1, y1, x2, y2):
    return {"bbox": [x1, y1, x2, y2], "conf": 0.9}


def _forklift(x1, y1, x2, y2):
    return {"bbox": [x1, y1, x2, y2], "conf": 0.9}


def test_bbox_center():
    assert bbox_center([0, 0, 10, 20]) == (5.0, 10.0)


def test_no_people_or_no_forklifts_means_no_violations():
    checker = DangerZoneChecker(proximity_px=150)
    assert checker.check([], [_forklift(0, 0, 50, 50)], 1920, 1080) == []
    assert checker.check([_person(0, 0, 50, 50)], [], 1920, 1080) == []
    assert checker.check([], [], 1920, 1080) == []


def test_person_far_from_forklift_is_not_flagged():
    checker = DangerZoneChecker(proximity_px=150)
    people = [_person(0, 0, 40, 80)]          # center ~ (20, 40)
    forklifts = [_forklift(1500, 900, 1600, 1000)]  # far away
    assert checker.check(people, forklifts, 1920, 1080) == []


def test_person_near_forklift_is_flagged_with_no_configuration():
    """This is the headline requirement: works on ANY camera, zero setup."""
    checker = DangerZoneChecker()  # defaults only — nothing camera-specific
    people = [_person(100, 100, 140, 180)]        # center (120, 140)
    forklifts = [_forklift(150, 110, 220, 170)]    # center (185, 140) -> 65px away
    violations = checker.check(people, forklifts, 1920, 1080)
    assert len(violations) == 1
    assert violations[0]["type"] == "PERSON_NEAR_FORKLIFT"
    assert violations[0]["distance_px"] < DEFAULT_PROXIMITY_PX


def test_proximity_threshold_is_respected():
    checker = DangerZoneChecker(proximity_px=50)
    people = [_person(0, 0, 40, 40)]           # center (20, 20)
    forklifts = [_forklift(100, 0, 140, 40)]    # center (120, 20) -> 100px away
    # 100px > 50px threshold -> should NOT be flagged
    assert checker.check(people, forklifts, 1920, 1080) == []

    checker2 = DangerZoneChecker(proximity_px=150)
    # same geometry, wider threshold -> SHOULD be flagged
    violations = checker2.check(people, forklifts, 1920, 1080)
    assert len(violations) == 1


def test_point_in_polygon_basic_square():
    square = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert point_in_polygon((5.0, 5.0), square) is True
    assert point_in_polygon((15.0, 5.0), square) is False


def test_polygon_to_pixels_scales_normalized_points():
    norm = [(0.0, 0.0), (1.0, 1.0)]
    px = polygon_to_pixels(norm, width=1920, height=1080)
    assert px == [(0.0, 0.0), (1920.0, 1080.0)]


def test_danger_zone_polygon_flags_person_even_when_far_from_forklift():
    """The optional, per-camera zone check: a person standing in a configured
    danger zone is flagged as long as a forklift is active anywhere in frame,
    even if they aren't within plain pixel-distance of it."""
    danger_zone = [(0.0, 0.0), (0.2, 0.0), (0.2, 0.2), (0.0, 0.2)]  # top-left corner
    checker = DangerZoneChecker(proximity_px=10, danger_zone=danger_zone)
    people = [_person(10, 10, 50, 90)]  # center (30, 50) -> inside the zone in a 1920x1080 frame
    forklifts = [_forklift(1800, 900, 1900, 1000)]  # far away, well outside proximity_px
    violations = checker.check(people, forklifts, 1920, 1080)
    assert len(violations) == 1
    assert violations[0]["type"] == "PERSON_IN_DANGER_ZONE"


def test_from_profile_reads_proximity_and_zone():
    profile = {"proximity_px": 200, "danger_zone": [[0, 0], [1, 0], [1, 1], [0, 1]]}
    checker = DangerZoneChecker.from_profile(profile)
    assert checker.proximity_px == 200
    assert checker.danger_zone_norm == [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


def test_from_profile_defaults_when_missing_keys():
    checker = DangerZoneChecker.from_profile({})
    assert checker.proximity_px == 150
    assert checker.danger_zone_norm is None
