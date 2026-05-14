# core/gestures.py
"""
Gesture recognition state machine.

Processes a list of 21 MediaPipe landmarks per frame and emits
cursor events (move, click, drag, scroll) to the actuator.

Gesture definitions:

  CURSOR MOVE:
    Landmark 8 (index tip) controls cursor position.
    Coordinates pass through the 1€ Filter before actuation.
    Active only when no other gesture is active.

  LEFT CLICK:
    Euclidean distance between landmark 8 (index tip) and landmark 12 (middle tip)
    drops below CLICK_DISTANCE_THRESHOLD.
    A boolean cooldown flag prevents re-triggering within GESTURE_COOLDOWN_SECONDS.

  RIGHT CLICK:
    Euclidean distance between landmark 8 (index tip) and landmark 16 (ring tip)
    drops below RIGHT_CLICK_DISTANCE_THRESHOLD.
    Same cooldown mechanism.

  DRAG & DROP:
    Left-click pinch (8–12 distance < threshold) maintained for > DRAG_HOLD_SECONDS.
    Activates mouse.press(). Cursor continues to track landmark 8.
    Releases on pinch break.

  SCROLL UP (three-finger open):
    Landmarks 8, 12, 16 are all extended (their y < their PIP joint y:
    lm8.y < lm6.y, lm12.y < lm10.y, lm16.y < lm14.y).
    AND thumb (lm4.y > lm2.y) and pinky (lm20.y > lm18.y) are folded.
    Emits positive scroll ticks. Cooldown applies.

  SCROLL DOWN (pinky extension):
    Landmark 20 is extended (lm20.y < lm18.y).
    AND landmarks 8, 12, 16 are all curled (lm8.y > lm6.y, lm12.y > lm10.y, lm16.y > lm14.y).
    Emits negative scroll ticks. Cooldown applies.

Coordinate note:
  MediaPipe y=0.0 is the TOP of the frame. Lower y means higher in the image.
  "Extended" = tip y < PIP y (tip is ABOVE its proximal joint = finger is pointing up).
  "Curled"   = tip y > PIP y (tip is BELOW its proximal joint = finger is bent down).
"""

import time
import logging
from enum import Enum, auto

import numpy as np

from core.tracker import Landmark
from core.tracker import (
    LM_INDEX_TIP, LM_INDEX_PIP,
    LM_MIDDLE_TIP, LM_MIDDLE_PIP,
    LM_RING_TIP, LM_RING_PIP,
    LM_PINKY_TIP, LM_PINKY_PIP,
    LM_THUMB_TIP, LM_THUMB_MCP,
)
from core.filter import OneEuroFilter
from core.display import VirtualDesktop, TrackpadZone, map_to_desktop
from core.actuator import MouseActuator
from config import (
    CAMERA_FPS,
    CLICK_DISTANCE_THRESHOLD,
    RIGHT_CLICK_DISTANCE_THRESHOLD,
    DRAG_HOLD_SECONDS,
    GESTURE_COOLDOWN_SECONDS,
    SCROLL_TICKS,
    ONE_EURO_MINCUTOFF,
    ONE_EURO_BETA,
    ONE_EURO_DCUTOFF,
)

logger = logging.getLogger(__name__)


class GestureState(Enum):
    IDLE = auto()
    LEFT_PINCH_PENDING_DRAG = auto()    # Pinch detected, waiting for drag threshold
    DRAGGING = auto()


def _distance(a: Landmark, b: Landmark) -> float:
    """3D Euclidean distance in normalized MediaPipe coordinate space."""
    return float(np.linalg.norm([a.x - b.x, a.y - b.y, a.z - b.z]))


def _is_extended(tip: Landmark, pip: Landmark) -> bool:
    """Finger is extended when tip is above (lower y value than) its PIP joint."""
    return tip.y < pip.y


def _is_curled(tip: Landmark, pip: Landmark) -> bool:
    return tip.y > pip.y


class GestureProcessor:
    """
    Stateful gesture processor. Call process() once per frame.

    Args:
        actuator: MouseActuator instance to send events to
        desktop:  VirtualDesktop for coordinate mapping
        trackpad: TrackpadZone for coordinate mapping
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

        # One 1€ Filter per axis — independent smoothing
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

        self._state = GestureState.IDLE
        self._pinch_start_time: float | None = None
        self._last_gesture_time: float = 0.0

    def _in_cooldown(self, now: float) -> bool:
        return (now - self._last_gesture_time) < GESTURE_COOLDOWN_SECONDS

    def _register_gesture(self, now: float) -> None:
        self._last_gesture_time = now

    def process(self, landmarks: list[Landmark]) -> None:
        """
        Process one frame's landmarks and emit appropriate actuator calls.
        Must be called at frame rate — the 1€ Filter assumes consistent timing.
        """
        now = time.perf_counter()

        idx_tip  = landmarks[LM_INDEX_TIP]
        idx_pip  = landmarks[LM_INDEX_PIP]
        mid_tip  = landmarks[LM_MIDDLE_TIP]
        mid_pip  = landmarks[LM_MIDDLE_PIP]
        rng_tip  = landmarks[LM_RING_TIP]
        rng_pip  = landmarks[LM_RING_PIP]
        pnk_tip  = landmarks[LM_PINKY_TIP]
        pnk_pip  = landmarks[LM_PINKY_PIP]
        thb_tip  = landmarks[LM_THUMB_TIP]
        thb_mcp  = landmarks[LM_THUMB_MCP]

        # ── Compute distances ─────────────────────────────────────────────────
        d_left   = _distance(idx_tip, mid_tip)    # index–middle → left click
        d_right  = _distance(idx_tip, rng_tip)    # index–ring   → right click

        # ── Gesture detection ─────────────────────────────────────────────────

        # 1. Check scroll gestures first (take priority, no cursor movement)
        scroll_up_detected = (
            _is_extended(idx_tip, idx_pip)
            and _is_extended(mid_tip, mid_pip)
            and _is_extended(rng_tip, rng_pip)
            and _is_curled(thb_tip, thb_mcp)
            and _is_curled(pnk_tip, pnk_pip)
        )

        scroll_down_detected = (
            _is_extended(pnk_tip, pnk_pip)
            and _is_curled(idx_tip, idx_pip)
            and _is_curled(mid_tip, mid_pip)
            and _is_curled(rng_tip, rng_pip)
        )

        if scroll_up_detected and not self._in_cooldown(now):
            self._actuator.scroll(SCROLL_TICKS)
            self._register_gesture(now)
            # Reset drag timer to prevent accidental drag activation after scroll
            if self._state == GestureState.LEFT_PINCH_PENDING_DRAG:
                self._pinch_start_time = now
            return

        if scroll_down_detected and not self._in_cooldown(now):
            self._actuator.scroll(-SCROLL_TICKS)
            self._register_gesture(now)
            if self._state == GestureState.LEFT_PINCH_PENDING_DRAG:
                self._pinch_start_time = now
            return

        # 2. Right click (only when not in a pending-drag state to avoid
        #    stealing the cooldown and suppressing the subsequent left-click)
        if (d_right < RIGHT_CLICK_DISTANCE_THRESHOLD
                and not self._in_cooldown(now)
                and self._state != GestureState.LEFT_PINCH_PENDING_DRAG
                and self._state != GestureState.DRAGGING):
            self._actuator.right_click()
            self._register_gesture(now)
            logger.debug("Right click (d=%.4f)", d_right)
            return

        # 3. Left click / drag state machine
        # Suppress click when index+middle+ring are all extended (scroll-up hand position).
        # Even if tips happen to be close, user intent is scroll not click.
        scroll_hand_shape = (
            _is_extended(idx_tip, idx_pip)
            and _is_extended(mid_tip, mid_pip)
            and _is_extended(rng_tip, rng_pip)
        )
        left_pinch_active = d_left < CLICK_DISTANCE_THRESHOLD and not scroll_hand_shape

        if self._state == GestureState.IDLE:
            if left_pinch_active:
                self._state = GestureState.LEFT_PINCH_PENDING_DRAG
                self._pinch_start_time = now

        elif self._state == GestureState.LEFT_PINCH_PENDING_DRAG:
            if not left_pinch_active:
                # Pinch released before drag threshold — fire discrete left click
                if not self._in_cooldown(now):
                    self._actuator.left_click()
                    self._register_gesture(now)
                    logger.debug("Left click (d=%.4f)", d_left)
                self._state = GestureState.IDLE
                self._pinch_start_time = None
            elif (now - self._pinch_start_time) >= DRAG_HOLD_SECONDS:
                # Pinch held long enough — transition to drag
                self._actuator.drag_start()
                self._state = GestureState.DRAGGING
                logger.debug("Drag start (held %.3fs)", now - self._pinch_start_time)

        elif self._state == GestureState.DRAGGING:
            if not left_pinch_active:
                self._actuator.drag_end()
                self._state = GestureState.IDLE
                self._pinch_start_time = None

        # 4. Cursor movement — always runs (even during drag)
        raw_x = idx_tip.x
        raw_y = idx_tip.y

        filtered_x = self._filter_x(raw_x, now)
        filtered_y = self._filter_y(raw_y, now)

        screen_x, screen_y = map_to_desktop(filtered_x, filtered_y, self._trackpad, self._desktop)
        self._actuator.move(screen_x, screen_y)
