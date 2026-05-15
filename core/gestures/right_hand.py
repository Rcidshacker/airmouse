# core/gestures/right_hand.py
"""
Right-hand gesture processor.

State machine:
  IDLE
    ├─ fist                      → LOCKED
    ├─ peace sign                → SCROLLING
    └─ thumb+index pinch         → LEFT_PINCH_PENDING_DRAG

  LOCKED
    └─ any finger extends        → IDLE

  SCROLLING
    ├─ wrist flick up            → scroll(+ticks)  [stay SCROLLING]
    ├─ wrist flick down          → scroll(-ticks)  [stay SCROLLING]
    └─ peace sign released       → IDLE

  LEFT_PINCH_PENDING_DRAG
    ├─ pinch released < DRAG_HOLD_SECONDS  → left_click() or double_click() → IDLE
    └─ pinch held ≥ DRAG_HOLD_SECONDS      → drag_start() → DRAGGING

  DRAGGING
    └─ pinch released            → drag_end() → IDLE
"""

import time
import logging
from enum import Enum, auto

from config import (
    CAMERA_FPS,
    THUMB_INDEX_CLICK_DIST,
    THUMB_MIDDLE_CLICK_DIST,
    DRAG_HOLD_SECONDS,
    GESTURE_COOLDOWN_SECONDS,
    DOUBLE_CLICK_WINDOW_S,
    WRIST_VELOCITY_THRESHOLD,
    SCROLL_TICK_SCALE,
    SCROLL_COOLDOWN_S,
    ONE_EURO_MINCUTOFF,
    ONE_EURO_BETA,
    ONE_EURO_DCUTOFF,
)
from core.tracker import Landmark
from core.filter import OneEuroFilter
from core.display import VirtualDesktop, TrackpadZone, map_to_desktop
from core.actuator import MouseActuator
from core.gestures.utils import dist3d, is_fist, is_peace_sign

logger = logging.getLogger(__name__)


class _State(Enum):
    IDLE = auto()
    LEFT_PINCH_PENDING_DRAG = auto()
    DRAGGING = auto()
    SCROLLING = auto()
    LOCKED = auto()


class RightHandProcessor:
    """
    Processes right-hand landmarks each frame.
    Call process(landmarks) where landmarks is list[Landmark] | None.
    None means no right hand detected this frame.
    """

    def __init__(
        self,
        actuator: MouseActuator,
        desktop: VirtualDesktop,
        trackpad: TrackpadZone,
    ) -> None:
        self._actuator = actuator
        self._desktop = desktop
        self._trackpad = trackpad
        self._state = _State.IDLE
        self._pinch_start_time: float | None = None
        self._last_click_time: float = 0.0
        self._last_gesture_time: float = 0.0
        self._last_scroll_time: float = 0.0
        self._prev_wrist_y: float | None = None
        self._last_frame_time: float | None = None
        self._filter_x = OneEuroFilter(
            freq=float(CAMERA_FPS),
            mincutoff=ONE_EURO_MINCUTOFF,
            beta=ONE_EURO_BETA,
            dcutoff=ONE_EURO_DCUTOFF,
        )
        self._filter_y = OneEuroFilter(
            freq=float(CAMERA_FPS),
            mincutoff=ONE_EURO_MINCUTOFF,
            beta=ONE_EURO_BETA,
            dcutoff=ONE_EURO_DCUTOFF,
        )

    def process(self, landmarks: list[Landmark] | None) -> None:
        if landmarks is None:
            # Hand left frame — clean up drag if active
            if self._state == _State.DRAGGING:
                self._actuator.drag_end()
            self._state = _State.IDLE
            self._pinch_start_time = None
            self._prev_wrist_y = None
            self._last_frame_time = None
            return

        now = time.perf_counter()

        # Compute wrist velocity (landmark 0 = wrist joint)
        wrist_y = landmarks[0].y
        dt = (now - self._last_frame_time) if self._last_frame_time is not None else (1.0 / CAMERA_FPS)
        dt = max(dt, 1e-6)  # guard divide-by-zero
        wrist_vel_y = (
            (wrist_y - self._prev_wrist_y) / dt
            if self._prev_wrist_y is not None
            else 0.0
        )
        self._prev_wrist_y = wrist_y
        self._last_frame_time = now

        fist = is_fist(landmarks)
        peace = is_peace_sign(landmarks)
        d_thumb_idx = dist3d(landmarks[4], landmarks[8])
        d_thumb_mid = dist3d(landmarks[4], landmarks[12])
        thumb_idx_pinch = d_thumb_idx < THUMB_INDEX_CLICK_DIST

        # ── LOCKED state ──────────────────────────────────────────────────────
        if self._state == _State.LOCKED:
            if not fist:
                self._state = _State.IDLE
                logger.debug("Unlocked")
            return  # no cursor, no gestures while locked

        # ── Fist → LOCKED ─────────────────────────────────────────────────────
        if fist and self._state not in (_State.LEFT_PINCH_PENDING_DRAG, _State.DRAGGING):
            if self._state == _State.DRAGGING:
                self._actuator.drag_end()
            self._state = _State.LOCKED
            logger.debug("Locked (fist)")
            return

        # ── SCROLLING state ───────────────────────────────────────────────────
        if self._state == _State.SCROLLING:
            if not peace:
                self._state = _State.IDLE
                return
            if abs(wrist_vel_y) > WRIST_VELOCITY_THRESHOLD:
                if (now - self._last_scroll_time) >= SCROLL_COOLDOWN_S:
                    ticks = int(min(5, max(1, abs(wrist_vel_y) / SCROLL_TICK_SCALE)))
                    # Negative velocity = hand moved up (y=0 at top) = scroll up
                    self._actuator.scroll(ticks if wrist_vel_y < 0 else -ticks)
                    self._last_scroll_time = now
                    logger.debug("Scroll %s ticks=%d vel=%.4f", "up" if wrist_vel_y < 0 else "down", ticks, wrist_vel_y)
            return  # cursor suspended while scrolling

        # ── Enter SCROLLING ───────────────────────────────────────────────────
        if peace and self._state == _State.IDLE:
            self._state = _State.SCROLLING
            logger.debug("Entered scroll mode (peace sign)")
            return

        # ── Right click ───────────────────────────────────────────────────────
        if (
            d_thumb_mid < THUMB_MIDDLE_CLICK_DIST
            and self._state == _State.IDLE
            and (now - self._last_gesture_time) >= GESTURE_COOLDOWN_SECONDS
        ):
            self._actuator.right_click()
            self._last_gesture_time = now
            logger.debug("Right click (d=%.4f)", d_thumb_mid)
            return

        # ── Left click / drag state machine ───────────────────────────────────
        if self._state == _State.IDLE:
            if thumb_idx_pinch:
                self._state = _State.LEFT_PINCH_PENDING_DRAG
                self._pinch_start_time = now

        elif self._state == _State.LEFT_PINCH_PENDING_DRAG:
            if not thumb_idx_pinch:
                # Pinch released — fire click (double if within window)
                if (now - self._last_gesture_time) >= GESTURE_COOLDOWN_SECONDS:
                    if (now - self._last_click_time) <= DOUBLE_CLICK_WINDOW_S and self._last_click_time > 0:
                        self._actuator.double_click()
                        logger.debug("Double click")
                        self._last_click_time = 0.0  # reset so triple doesn't become double+double
                    else:
                        self._actuator.left_click()
                        logger.debug("Left click (d=%.4f)", d_thumb_idx)
                        self._last_click_time = now
                    self._last_gesture_time = now
                self._state = _State.IDLE
                self._pinch_start_time = None

            elif self._pinch_start_time is not None and (now - self._pinch_start_time) >= DRAG_HOLD_SECONDS:
                self._actuator.drag_start()
                self._state = _State.DRAGGING
                logger.debug("Drag start")

        elif self._state == _State.DRAGGING:
            if not thumb_idx_pinch:
                self._actuator.drag_end()
                self._state = _State.IDLE
                self._pinch_start_time = None
                logger.debug("Drag end")

        # ── Cursor movement (IDLE and DRAGGING only) ──────────────────────────
        filtered_x = self._filter_x(landmarks[8].x, now)  # index tip
        filtered_y = self._filter_y(landmarks[8].y, now)
        screen_x, screen_y = map_to_desktop(filtered_x, filtered_y, self._trackpad, self._desktop)
        self._actuator.move(screen_x, screen_y)
