# core/gestures/two_hand.py
"""
Two-hand gesture processor — power gestures requiring both hands visible.

Gestures:
  Both thumb+index pinch + wrists spread   → zoom in  (Ctrl+=)
  Both thumb+index pinch + wrists close    → zoom out (Ctrl+-)
  Both fists held ≥ LOCK_SCREEN_HOLD_S     → Win+L
  Left open palm + right fist swipe left   → Win+Left (snap left)
  Left open palm + right fist swipe right  → Win+Right (snap right)
"""

import time
import logging

from config import (
    GESTURE_COOLDOWN_SECONDS,
    ZOOM_WRIST_DELTA,
    LOCK_SCREEN_HOLD_S,
    WRIST_VELOCITY_THRESHOLD,
    CAMERA_FPS,
)
from core.tracker import Landmark
from core.actuator import MouseActuator
from core.gestures.utils import dist3d, is_fist, is_open_palm

logger = logging.getLogger(__name__)

_THUMB_INDEX_DIST = 0.045


class TwoHandProcessor:
    """
    Processes both-hand landmarks each frame.
    Call process(left_lm, right_lm) when both hands are visible.
    """

    def __init__(self, actuator: MouseActuator) -> None:
        self._actuator = actuator
        self._last_gesture_time: float = 0.0
        self._prev_wrist_dist: float | None = None
        self._both_fists_since: float | None = None
        self._lock_fired: bool = False
        self._last_frame_time: float | None = None
        self._prev_right_wrist_x: float | None = None

    def process(self, left_lm: list[Landmark], right_lm: list[Landmark]) -> None:
        now = time.perf_counter()
        dt = (now - self._last_frame_time) if self._last_frame_time is not None else (1.0 / CAMERA_FPS)
        dt = max(dt, 1e-6)
        self._last_frame_time = now

        in_cooldown = (now - self._last_gesture_time) < GESTURE_COOLDOWN_SECONDS

        left_fist = is_fist(left_lm)
        right_fist = is_fist(right_lm)
        left_open = is_open_palm(left_lm)
        left_pinch = dist3d(left_lm[4], left_lm[8]) < _THUMB_INDEX_DIST
        right_pinch = dist3d(right_lm[4], right_lm[8]) < _THUMB_INDEX_DIST

        # Right wrist x-velocity for snap gestures
        right_wrist_x = right_lm[0].x

        # ── Lock screen: both fists held ≥ LOCK_SCREEN_HOLD_S ────────────────
        if left_fist and right_fist:
            if self._both_fists_since is None:
                self._both_fists_since = now
                self._lock_fired = False
            elif (
                not self._lock_fired
                and (now - self._both_fists_since) >= LOCK_SCREEN_HOLD_S
            ):
                self._actuator.win_l()
                self._lock_fired = True
                logger.debug("Lock screen (Win+L)")
            return
        else:
            self._both_fists_since = None
            self._lock_fired = False

        if in_cooldown:
            self._prev_wrist_dist = None
            return

        # ── Zoom: both hands pinching, wrists spread/close ────────────────────
        if left_pinch and right_pinch:
            wrist_dist = dist3d(left_lm[0], right_lm[0])
            if self._prev_wrist_dist is not None:
                delta = wrist_dist - self._prev_wrist_dist
                if delta > ZOOM_WRIST_DELTA:
                    self._actuator.zoom_in()
                    self._last_gesture_time = now
                    logger.debug("Zoom in (delta=%.3f)", delta)
                elif delta < -ZOOM_WRIST_DELTA:
                    self._actuator.zoom_out()
                    self._last_gesture_time = now
                    logger.debug("Zoom out (delta=%.3f)", delta)
            self._prev_wrist_dist = wrist_dist
            return

        self._prev_wrist_dist = None

        # ── Snap: left open palm + right fist wrist velocity ─────────────────
        if left_open and right_fist:
            right_wrist_vel_x = 0.0
            if self._prev_right_wrist_x is not None:
                right_wrist_vel_x = (right_wrist_x - self._prev_right_wrist_x) / dt
            self._prev_right_wrist_x = right_wrist_x

            snap_threshold = WRIST_VELOCITY_THRESHOLD * 1.5
            if right_wrist_vel_x > snap_threshold:
                self._actuator.win_snap_right()
                self._last_gesture_time = now
                logger.debug("Snap right (Win+Right)")
            elif right_wrist_vel_x < -snap_threshold:
                self._actuator.win_snap_left()
                self._last_gesture_time = now
                logger.debug("Snap left (Win+Left)")
        else:
            self._prev_right_wrist_x = None
