"""Live video monitoring service shared by the API."""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, Optional

import cv2
import numpy as np

from ..config import Config
from ..monitor import ComplianceMonitor
from ..camera_profiles import resolve_profile
from . import store


class LiveMonitorService:
    """Runs ComplianceMonitor on a video/camera and exposes latest frame + stats.

    File playback runs at ~1× wall-clock: the display loop advances the video
    in realtime while YOLO inference runs on a background thread and sticky
    overlays are re-painted onto each display frame.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._infer_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._running = False
        self._source: Any = None
        self._monitor: Optional[ComplianceMonitor] = None
        self._latest_jpeg: Optional[bytes] = None
        self._stats: Dict[str, Any] = {
            "running": False,
            "source": None,
            "profile": None,
            "fps": 0.0,
            "frame": 0,
            "workers": 0,
            "forklifts": 0,
            "forklift_speed_kmh": 0.0,
            "forklift_speed_limit_kmh": 8.0,
            "forklift_overspeed": False,
            "road_ways": 0,
            "violations_session": 0,
            "last_alert": None,
            "status": "idle",
            "aisle_locked": False,
        }
        self._frame_count = 0
        self._t0 = 0.0
        self._session_id: Optional[int] = None
        self._infer_fps = 0.0
        self._pending_frame: Optional[np.ndarray] = None
        self._pending_seq = 0
        self._pending_video_t = 0.0
        self._pending_lock = threading.Lock()
        # One DB row per alert type per cooldown — not every YOLO frame
        self._last_logged: Dict[str, float] = {}
        self._log_cooldown_s = float(getattr(Config, "ALERT_LOG_COOLDOWN_S", 30.0))

    @property
    def running(self) -> bool:
        return self._running

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)

    def latest_jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._latest_jpeg

    def start(self, source: str, camera_id: Optional[str] = None) -> Dict[str, Any]:
        if self._running:
            self.stop()
            time.sleep(0.3)

        path = source
        if not str(source).isdigit():
            if not os.path.isabs(source):
                cand = os.path.join(Config.PROJECT_ROOT, source)
                if os.path.isfile(cand):
                    path = cand
                elif os.path.isfile(os.path.join(Config.DATA_DIR, "videos", os.path.basename(source))):
                    path = os.path.join(Config.DATA_DIR, "videos", os.path.basename(source))
            if not os.path.isfile(path):
                raise FileNotFoundError(f"Video not found: {source}")

        # camera_id is the real, stable identity for a deployed camera — pass
        # it explicitly whenever you have one (e.g. "loading_dock_1"). It is
        # looked up as an exact key in config/cameras.json; falling back to
        # the file name is only for ad-hoc local testing, and is a single
        # exact-key lookup too, not pattern matching against known clips.
        profile = resolve_profile(
            path if not str(source).isdigit() else source,
            camera_id=camera_id,
        )
        self._source = int(path) if str(path).isdigit() else path
        self._stop.clear()
        self._last_logged = {}
        with self._lock:
            self._stats.update({
                "running": False,
                "status": "starting",
                "last_alert": None,
                "source": str(self._source),
                "profile": profile.get("name"),
                "frame": 0,
                "fps": 0.0,
                "violations_session": 0,
                "workers": 0,
                "forklifts": 0,
                "forklift_speed_kmh": 0.0,
                "forklift_speed_limit_kmh": float(getattr(Config, "FORKLIFT_SPEED_LIMIT_KMH", 8.0)),
                "forklift_overspeed": False,
                "road_ways": 0,
                "aisle_locked": False,
            })
            self._latest_jpeg = None
        self._thread = threading.Thread(target=self._loop, args=(profile,), daemon=True)
        self._thread.start()
        for _ in range(200):
            st = self._stats.get("status")
            if self._running or st in ("error", "online", "alert"):
                break
            time.sleep(0.1)
        return self.status()

    def stop(self) -> Dict[str, Any]:
        self._stop.set()
        if self._infer_thread and self._infer_thread.is_alive():
            self._infer_thread.join(timeout=3.0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._running = False
        viol = int(self._stats.get("violations_session") or 0)
        store.end_session(self._session_id, frames=self._frame_count, violations=viol)
        self._session_id = None
        with self._lock:
            self._stats["running"] = False
            self._stats["status"] = "stopped"
        return self.status()

    def _encode_frame(self, result: np.ndarray, playback_label: str) -> Optional[bytes]:
        display = result
        h, w = display.shape[:2]
        if w > 1600:
            scale = 1600 / float(w)
            display = cv2.resize(result, (1600, int(h * scale)))
        # Show playback speed (1.0x) + AI infer rate — not "video FPS"
        label = f"{playback_label}  AI {self._infer_fps:.1f}"
        cv2.putText(
            display,
            label,
            (display.shape[1] - 220, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            2,
        )
        ok, buf = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        return buf.tobytes() if ok else None

    def _publish(self, jpeg: Optional[bytes], display_fps: float, last_alert: Optional[str], alert: bool) -> None:
        mon = self._monitor
        ls = getattr(mon, "last_stats", None) or {}
        with self._lock:
            if jpeg:
                self._latest_jpeg = jpeg
            self._stats.update({
                "running": True,
                "fps": round(display_fps, 1),
                "frame": self._frame_count,
                "violations_session": len(mon.violations) if mon else 0,
                "last_alert": last_alert or self._stats.get("last_alert"),
                "status": "alert" if alert else "online",
                "workers": int(ls.get("workers", 0)),
                "forklifts": int(ls.get("forklifts", 0)),
                "forklift_speed_kmh": float(ls.get("forklift_speed_kmh", 0.0) or 0.0),
                "forklift_speed_limit_kmh": float(
                    ls.get("forklift_speed_limit_kmh")
                    or getattr(Config, "FORKLIFT_SPEED_LIMIT_KMH", 8.0)
                ),
                "forklift_overspeed": bool(ls.get("forklift_overspeed", False)),
                "road_ways": int(ls.get("yellow_lines", 0)),
                "aisle_locked": bool(ls.get("aisle_locked", False)),
            })

    def _labels_locked(self) -> bool:
        mon = self._monitor
        if mon is None:
            return False
        if getattr(mon, "is_project16", False):
            return True
        if getattr(mon, "is_sawant", False) or not getattr(mon, "_enable_yellow_lines", True):
            return True
        if getattr(mon, "is_safe_route", False):
            return bool(getattr(mon, "_safe_route_frozen", False))
        return bool(getattr(mon, "_aisle_road_frozen", False))

    def _log_violations(self, src: Any, profile: Dict[str, Any], violations: list) -> None:
        """Persist distinct alert onsets only (cooldown), not per-frame spam."""
        if not violations:
            return
        now = time.monotonic()
        seen_types = set()
        for v in violations:
            etype = v.get("type", "UNKNOWN") if isinstance(v, dict) else "UNKNOWN"
            if etype in seen_types:
                continue
            seen_types.add(etype)
            last = self._last_logged.get(etype, 0.0)
            if now - last < self._log_cooldown_s:
                continue
            self._last_logged[etype] = now
            sev = "high" if etype in (
                "NO_HELMET",
                "FORKLIFT_OVERSPEED",
                "PERSON_IN_DANGER_ZONE",
                "PERSON_NEAR_FORKLIFT",
                "PERSON_PRODUCT_TOUCH",
                "PERSON_PRODUCT_TOUCH_TIME",
                "MAN_NEAR_CONVEYOR",
                "NO_SAFETY_HARNESS",
            ) else "medium"
            payload = dict(v) if isinstance(v, dict) else {"raw": v}
            ls = getattr(self._monitor, "last_stats", None) or {}
            payload["workers"] = int(ls.get("workers", 0))
            store.add_event(
                etype,
                source=str(src),
                profile=profile.get("name", ""),
                severity=sev,
                payload=payload,
            )

    @staticmethod
    def _skip_to_realtime(
        cap: cv2.VideoCapture,
        *,
        file_frame_i: int,
        playback_t0: float,
        video_fps: float,
        stop_event: threading.Event,
    ) -> int:
        """Drop frames so file playback stays ~1× wall-clock."""
        elapsed = max(time.time() - playback_t0, 0.0)
        target = int(elapsed * video_fps)
        max_skip = max(1, target - file_frame_i)
        skipped = 0
        while file_frame_i < target and skipped < max_skip and not stop_event.is_set():
            if not cap.grab():
                break
            file_frame_i += 1
            skipped += 1
        return file_frame_i

    def _infer_worker(self, src: Any, profile: Dict[str, Any]) -> None:
        """Background YOLO — updates sticky overlay; never blocks display loop."""
        last_seq = -1
        infer_n = 0
        infer_t0 = time.time()
        while not self._stop.is_set():
            with self._pending_lock:
                frame = None if self._pending_frame is None else self._pending_frame.copy()
                seq = self._pending_seq
                video_t = float(self._pending_video_t)
            if frame is None or seq == last_seq or self._monitor is None:
                time.sleep(0.005)
                continue
            last_seq = seq
            try:
                self._monitor._motion_clock = video_t
                _result, violations = self._monitor.process_frame(frame)
            except Exception as exc:
                print(f"Live infer error: {exc}")
                time.sleep(0.05)
                continue
            infer_n += 1
            elapsed = max(time.time() - infer_t0, 1e-6)
            self._infer_fps = infer_n / elapsed
            self._log_violations(src, profile, violations)
            # Refresh stats panel without waiting for display tick
            last_alert = violations[-1].get("type") if violations else None
            with self._lock:
                ls = getattr(self._monitor, "last_stats", None) or {}
                self._stats.update({
                    "workers": int(ls.get("workers", 0)),
                    "forklifts": int(ls.get("forklifts", 0)),
                    "forklift_speed_kmh": float(ls.get("forklift_speed_kmh", 0.0) or 0.0),
                    "forklift_speed_limit_kmh": float(
                        ls.get("forklift_speed_limit_kmh")
                        or getattr(Config, "FORKLIFT_SPEED_LIMIT_KMH", 8.0)
                    ),
                    "forklift_overspeed": bool(ls.get("forklift_overspeed", False)),
                    "road_ways": int(ls.get("yellow_lines", 0)),
                    "aisle_locked": bool(ls.get("aisle_locked", False)),
                    "violations_session": len(self._monitor.violations),
                    "last_alert": last_alert or self._stats.get("last_alert"),
                    "status": "alert" if violations else "online",
                })

    def _loop(self, profile: Dict[str, Any]) -> None:
        src = self._source
        try:
            try:
                self._monitor = ComplianceMonitor(profile=profile)
            except Exception as e:
                err = str(e)
                if "_regex" in err or "Application Control" in err or "DLL load failed" in err:
                    fallback = os.path.join(Config.PROJECT_ROOT, "yolo26m.pt")
                    if not os.path.exists(fallback):
                        fallback = "yolo26m.pt"
                    print(f"Live: retrying with fallback model {fallback}")
                    self._monitor = ComplianceMonitor(model_path=fallback, profile=profile)
                else:
                    raise

            cap = cv2.VideoCapture(src)
            if not cap.isOpened():
                with self._lock:
                    self._stats["status"] = "error"
                    self._stats["last_alert"] = f"Cannot open source: {src}"
                return

            is_file = not str(src).isdigit()
            video_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            if video_fps < 1.0:
                video_fps = 25.0
            # Pace display at the video's native FPS (true 1× playback)
            display_fps_cap = video_fps
            frame_interval = 1.0 / max(display_fps_cap, 1.0)

            self._running = True
            self._frame_count = 0
            self._t0 = time.time()
            self._infer_fps = 0.0
            file_frame_i = 0
            self._session_id = store.start_session(
                source=str(src),
                profile=profile.get("name", ""),
            )
            with self._lock:
                self._stats.update({
                    "running": True,
                    "source": str(src),
                    "profile": profile.get("name"),
                    "status": "starting",
                    "violations_session": 0,
                    "last_alert": None,
                })
            with self._pending_lock:
                self._pending_frame = None
                self._pending_seq = 0
                self._pending_video_t = 0.0

            # Optional short warm-up only when aisle/route labels must lock
            if not self._labels_locked():
                warm_deadline = time.time() + 8.0
                warm_processed = 0
                while (
                    not self._stop.is_set()
                    and warm_processed < 24
                    and time.time() < warm_deadline
                    and not self._labels_locked()
                ):
                    if is_file:
                        for _ in range(max(1, int(video_fps * 0.4))):
                            if not cap.grab():
                                break
                            file_frame_i += 1
                    ret, frame = cap.read()
                    if not ret:
                        break
                    file_frame_i += 1
                    result, violations = self._monitor.process_frame(frame)
                    warm_processed += 1
                    self._frame_count += 1
                    self._log_violations(src, profile, violations)
                    jpeg = self._encode_frame(result, "1.0x")
                    last_alert = violations[-1].get("type") if violations else None
                    self._publish(jpeg, warm_processed / max(time.time() - self._t0, 1e-6), last_alert, bool(violations))

            with self._lock:
                self._stats["status"] = "online"
                self._stats["aisle_locked"] = self._labels_locked()
            print(
                f"Live ready: profile={profile.get('name')} "
                f"frame={self._frame_count} locked={self._labels_locked()} "
                f"playback=1x@{video_fps:.0f}fps (display≤{display_fps_cap:.0f})"
            )

            self._infer_thread = threading.Thread(
                target=self._infer_worker, args=(src, profile), daemon=True
            )
            self._infer_thread.start()

            playback_t0 = time.time()
            playback_base_frame = file_frame_i
            next_show_t = time.time()

            while not self._stop.is_set():
                if is_file:
                    ahead = self._skip_to_realtime(
                        cap,
                        file_frame_i=file_frame_i - playback_base_frame,
                        playback_t0=playback_t0,
                        video_fps=video_fps,
                        stop_event=self._stop,
                    )
                    file_frame_i = playback_base_frame + ahead

                ret, frame = cap.read()
                if not ret:
                    if is_file:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        file_frame_i = 0
                        playback_base_frame = 0
                        playback_t0 = time.time()
                        next_show_t = time.time()
                        continue
                    break
                file_frame_i += 1

                # Hand latest frame + video clock to YOLO worker (non-blocking)
                with self._pending_lock:
                    self._pending_frame = frame
                    self._pending_seq += 1
                    self._pending_video_t = (
                        float(file_frame_i) / float(video_fps) if is_file else time.time()
                    )

                # Paint sticky detections onto this realtime frame (no YOLO wait)
                display = self._monitor.render_overlay_on(frame)
                self._frame_count += 1
                elapsed = max(time.time() - self._t0, 1e-6)
                disp_fps = self._frame_count / elapsed

                jpeg = self._encode_frame(display, "1.0x")
                alert = self._stats.get("status") == "alert"
                self._publish(jpeg, disp_fps, self._stats.get("last_alert"), alert)

                # Pace display to ~1× video (capped)
                next_show_t += frame_interval
                delay = next_show_t - time.time()
                if delay > 0.001:
                    time.sleep(min(delay, frame_interval))
                elif delay < -0.5:
                    # Fell far behind encode — resync clock
                    next_show_t = time.time()

            cap.release()
            if self._monitor:
                self._monitor.save_report()
        except Exception as exc:
            with self._lock:
                self._stats["status"] = "error"
                self._stats["last_alert"] = str(exc)
                self._stats["running"] = False
        finally:
            self._stop.set()
            if self._infer_thread and self._infer_thread.is_alive():
                self._infer_thread.join(timeout=2.0)
            viol = int(self._stats.get("violations_session") or 0)
            store.end_session(self._session_id, frames=self._frame_count, violations=viol)
            self._session_id = None
            self._running = False
            with self._lock:
                self._stats["running"] = False
                if self._stats.get("status") not in ("error", "stopped"):
                    self._stats["status"] = "stopped"


live_service = LiveMonitorService()
