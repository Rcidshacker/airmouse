# core/gestures/left_hand.py
"""
Left-hand gesture processor — Windows system shortcuts.

Gestures fire at most once per GESTURE_COOLDOWN_SECONDS.
All gestures are optional — right-hand behavior is unaffected if left hand absent.

Gesture map:
  Open palm (all 5 extended)       → Win+D (Show Desktop)
  V-sign (index+middle up)         → Alt+Tab (cycle windows)
  Four fingers (index–pinky up)    → Win+Tab (Task View)
  Thumb+index pinch                → Win key (Start Menu)
  Fist held                        → Ctrl modifier (held until fist released)
  Index pointing + wrist swipe →   → Alt+Left (Go Back)
"""

import time
import logging

from config import GESTURE_COOLDOWN_SECONDS, WRIST_VELOCITY_THRESHOLD, CAMERA_FPS
from core.tracker import Landmark
from core.actuator import MouseActuator
from core.gestures.utils import (
    dist3d, is_fist, is_open_palm, is_v_sign, is_four_fingers,
)

logger = logging.getLogger(__name__)

_THUMB_INDEX_DIST = 0.045   # local threshold — left hand pinch for Win key
_SWIPE_VELOCITY   = 0.012   # wrist x-velocity threshold for Go Back swipe


class LeftHandProcessor:
    """
    Processes left-hand landmarks each frame.
    Call process(landmarks) where landmarks is list[Landmark] | None.
    """

    def __init__(self, actuator: MouseActuator) -> None:
        self._actuator = actuator
        self._last_gesture_time: float = 0.0
        self._ctrl_held: bool = False
        self._prev_wrist_x: float | None = None
        self._last_frame_time: float | None = None

    def process(self, landmarks: list[Landmark] | None) -> None:
        if landmarks is None:
            # Release Ctrl if held when hand leaves frame
            if self._ctrl_held:
                self._actuator.ctrl_up()
                self._ctrl_held = False
            self._prev_wrist_x = None
            self._last_frame_time = None
            return

        now = time.perf_counter()
        in_cooldown = (now - self._last_gesture_time) < GESTURE_COOLDOWN_SECONDS

        # Wrist x-velocity for swipe detection
        wrist_x = landmarks[0].x
        dt = (now - self._last_frame_time) if self._last_frame_time is not None else (1.0 / CAMERA_FPS)
        dt = max(dt, 1e-6)
        wrist_vel_x = (
            (wrist_x - self._prev_wrist_x) / dt
            if self._prev_wrist_x is not None
            else 0.0
        )
        self._prev_wrist_x = wrist_x
        self._last_frame_time = now

        fist = is_fist(landmarks)
        open_palm = is_open_palm(landmarks)
        v_sign = is_v_sign(landmarks)
        four_fin = is_four_fingers(landmarks)
        thumb_idx = dist3d(landmarks[4], landmarks[8]) < _THUMB_INDEX_DIST
        # Index pointing = index extended, others curled
        index_pointing = (
            landmarks[8].y < landmarks[6].y
            and landmarks[12].y > landmarks[10].y
            and landmarks[16].y > landmarks[14].y
            and landmarks[20].y > landmarks[18].y
        )

        # Ctrl modifier — fist held = Ctrl down, fist released = Ctrl up
        if fist and not self._ctrl_held:
            self._actuator.ctrl_down()
            self._ctrl_held = True
            logger.debug("Ctrl down (left fist)")
            return
        if not fist and self._ctrl_held:
            self._actuator.ctrl_up()
            self._ctrl_held = False
            logger.debug("Ctrl up")

        if self._ctrl_held:
            return  # while Ctrl held, suppress other left-hand gestures

        if in_cooldown:
            return

        # Gesture detection (priority order)
        if open_palm:
            self._actuator.win_d()
            self._last_gesture_time = now
            logger.debug("Show Desktop (Win+D)")

        elif v_sign:
            self._actuator.alt_tab()
            self._last_gesture_time = now
            logger.debug("Alt+Tab")

        elif four_fin:
            self._actuator.win_tab()
            self._last_gesture_time = now
            logger.debug("Task View (Win+Tab)")

        elif thumb_idx:
            self._actuator.win_key()
            self._last_gesture_time = now
            logger.debug("Win key")

        elif index_pointing and wrist_vel_x > _SWIPE_VELOCITY:
            # Swipe right (from camera perspective = user's left-to-right swipe)
            self._actuator.alt_left()
            self._last_gesture_time = now
            logger.debug("Go Back (Alt+Left)")
