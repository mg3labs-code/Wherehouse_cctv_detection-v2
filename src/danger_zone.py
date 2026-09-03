"""Camera-agnostic person <-> forklift proximity / danger-zone checking.

This replaces the old approach of hand-tuning "is this person too close"
logic per demo video filename. It works two ways, and neither one needs to
know anything about which camera or clip it's looking at:

1. Distance check (always on, zero configuration): if a detected person's
   center point is within ``proximity_px`` of a detected forklift's center
   point, that's a violation. This alone works on literally any camera the
   moment it's plugged in.

2. Zone check (opt-in, per camera): if an operator has taken the time to
   draw a danger-zone polygon for a specific camera (in
   ``config/cameras.json``), a person whose body-center point falls inside
   that polygon while any forklift is active in the frame is also flagged.
   This is more precise once configured, but is never required to get a
   working check on day one.

Both checks operate purely on bounding boxes already produced by the
existing detector (see ``monitor.py``) — no new model, no per-video code.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

Point = Tuple[float, float]

DEFAULT_PROXIMITY_PX = 150.0


def bbox_center(bbox: Sequence[float]) -> Point:
    x1, y1, x2, y2 = bbox
    return (float(x1 + x2) / 2.0, float(y1 + y2) / 2.0)


def _distance(a: Point, b: Point) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def polygon_to_pixels(norm_points: Sequence[Sequence[float]], width: int, height: int) -> List[Point]:
    """Convert a list of normalized (0..1) [x, y] points to pixel coordinates."""
    return [(float(x) * width, float(y) * height) for x, y in norm_points]


def point_in_polygon(point: Point, polygon: Sequence[Point]) -> bool:
    """Standard ray-casting point-in-polygon test. No OpenCV dependency."""
    if not polygon or len(polygon) < 3:
        return False
    x, y = point
    inside = False
    n = len(polygon)
    x1, y1 = polygon[0]
    for i in range(1, n + 1):
        x2, y2 = polygon[i % n]
        if y > min(y1, y2) and y <= max(y1, y2) and x <= max(x1, x2):
            if y1 != y2:
                x_intersect = (y - y1) * (x2 - x1) / (y2 - y1) + x1
            else:
                x_intersect = x1
            if x1 == x2 or x <= x_intersect:
                inside = not inside
        x1, y1 = x2, y2
    return inside


class DangerZoneChecker:
    """Reusable, per-camera-configurable proximity + zone checker.

    Construct one from whatever profile dict the camera resolved to
    (see ``camera_profiles.py``) — no filename sniffing involved here.
    """

    def __init__(
        self,
        proximity_px: float = DEFAULT_PROXIMITY_PX,
        danger_zone: Optional[Sequence[Sequence[float]]] = None,
    ) -> None:
        self.proximity_px = float(proximity_px)
        # Stored normalized (0..1); converted to pixels per-frame since
        # frame size can vary (different cameras, different resolutions).
        self.danger_zone_norm: Optional[List[Point]] = (
            [(float(p[0]), float(p[1])) for p in danger_zone] if danger_zone else None
        )

    @classmethod
    def from_profile(cls, profile: Dict[str, Any]) -> "DangerZoneChecker":
        return cls(
            proximity_px=float(profile.get("proximity_px", DEFAULT_PROXIMITY_PX)),
            danger_zone=profile.get("danger_zone") or None,
        )

    def check(
        self,
        people: Sequence[Dict[str, Any]],
        forklifts: Sequence[Dict[str, Any]],
        frame_width: int,
        frame_height: int,
    ) -> List[Dict[str, Any]]:
        """Return a list of violation dicts. Empty list = nothing to flag.

        ``people`` and ``forklifts`` are the same detection dicts the rest
        of the pipeline already uses (each has a ``bbox`` key).
        """
        if not people or not forklifts:
            return []

        violations: List[Dict[str, Any]] = []
        zone_px = (
            polygon_to_pixels(self.danger_zone_norm, frame_width, frame_height)
            if self.danger_zone_norm
            else None
        )

        forklift_centers = [bbox_center(f["bbox"]) for f in forklifts]

        flagged_people: set = set()
        for p_idx, person in enumerate(people):
            p_center = bbox_center(person["bbox"])

            # 1. Zero-config distance check against every forklift in frame.
            nearest = min(
                (_distance(p_center, fc) for fc in forklift_centers),
                default=None,
            )
            if nearest is not None and nearest < self.proximity_px:
                violations.append({
                    "type": "PERSON_NEAR_FORKLIFT",
                    "distance_px": round(nearest, 1),
                    "threshold_px": self.proximity_px,
                })
                flagged_people.add(p_idx)
                continue

            # 2. Optional, more precise zone check (only if a zone is configured).
            if zone_px is not None and point_in_polygon(p_center, zone_px):
                violations.append({
                    "type": "PERSON_IN_DANGER_ZONE",
                    "point": [round(p_center[0], 1), round(p_center[1], 1)],
                })
                flagged_people.add(p_idx)

        return violations
