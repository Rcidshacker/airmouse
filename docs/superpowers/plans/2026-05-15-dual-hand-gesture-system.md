# Dual-Hand AVP-Style Gesture System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current single-hand index-middle gesture set with a dual-hand, thumb-trigger, wrist-scroll system modelled after Apple Vision Pro interaction philosophy.

**Architecture:** Right hand always active (cursor + thumb-pinch clicks + peace-sign wrist scroll + fist lock). Left hand optional system layer (Win shortcuts, Ctrl modifier). Two-hand gestures for zoom/snap/lock-screen. `core/gestures.py` replaced by `core/gestures/` package with one processor per hand role. `tracker.py` updated to track 2 hands and return `HandsResult`. `main.py` minimal change — swap import and remove `if landmarks is not None` guard.

**Tech Stack:** Python 3.13, MediaPipe 0.10.35 Tasks API, pynput (mouse + keyboard), ctypes SendInput, 1€ filter.

**Spec:** `docs/superpowers/specs/2026-05-15-dual-hand-gesture-system-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `config.py` | Add thumb-pinch, fist, wrist-velocity, zoom, lock-screen constants |
| Modify | `core/actuator.py` | Add `double_click()` + all keyboard system-shortcut methods |
| Modify | `core/tracker.py` | Add `HandsResult` dataclass; set `num_hands=2`; parse handedness |
| Create | `core/gestures/__init__.py` | Package init, exports `GestureOrchestrator` |
| Create | `core/gestures/utils.py` | Shared: `dist3d()`, `is_fist()`, `is_peace_sign()`, `is_open_palm()`, `is_v_sign()`, `is_four_fingers()` |
| Create | `core/gestures/right_hand.py` | `RightHandProcessor` — cursor, thumb-pinch clicks, drag, peace-sign wrist scroll, fist lock |
| Create | `core/gestures/left_hand.py` | `LeftHandProcessor` — Windows system shortcuts |
| Create | `core/gestures/two_hand.py` | `TwoHandProcessor` — zoom, snap, lock screen |
| Create | `core/gestures/orchestrator.py` | `GestureOrchestrator` — routes `HandsResult` to sub-processors |
| Delete | `core/gestures.py` | Replaced by package |
| Modify | `main.py` | Import `GestureOrchestrator`, pass `HandsResult` |
| Modify | `test_startup.py` | Update smoke test for new API |

---

## Task 1: Add new threshold constants to config.py

**Files:**
- Modify: `config.py`

- [ ] **Step 1: Add constants after existing gesture thresholds section**

In `config.py`, replace the entire gesture thresholds block:

```python
# ── Gesture Thresholds ────────────────────────────────────────────────────────
# All distances are Euclidean norms of normalized MediaPipe coordinates [0.0–1.0].

# Thumb-pinch thresholds
THUMB_INDEX_CLICK_DIST  = 0.045   # thumb tip ↔ index tip → left click
THUMB_MIDDLE_CLICK_DIST = 0.050   # thumb tip ↔ middle tip → right click

# Legacy (kept for reference during migration — unused after Task 5)
CLICK_DISTANCE_THRESHOLD = 0.03
RIGHT_CLICK_DISTANCE_THRESHOLD = 0.06

DRAG_HOLD_SECONDS = 0.4           # thumb+index pinch held → drag activates
GESTURE_COOLDOWN_SECONDS = 0.4    # min gap between discrete gesture events

DOUBLE_CLICK_WINDOW_S = 0.4       # second pinch within this window = double click

# Fist detection — all finger tips must be below their PIP joints
FIST_CURL_THRESHOLD = 0.0         # unused numerically; fist = all 5 curled (boolean)

# Wrist scroll (peace-sign posture)
WRIST_VELOCITY_THRESHOLD = 0.008  # normalized units/s — minimum wrist flick to register
SCROLL_TICK_SCALE        = 0.003  # velocity / scale = tick count (clamped 1–5)
SCROLL_COOLDOWN_S        = 0.12   # minimum gap between scroll emissions

# Scroll: number of OS scroll ticks per gesture detection cycle (legacy fallback)
SCROLL_TICKS = 3

# Two-hand gestures
ZOOM_WRIST_DELTA    = 0.05        # normalized wrist-to-wrist distance change per zoom tick
LOCK_SCREEN_HOLD_S  = 1.0         # both fists held this long → Win+L
```

- [ ] **Step 2: Verify import works**

```powershell
.\.venv\Scripts\python.exe -c "from config import THUMB_INDEX_CLICK_DIST, WRIST_VELOCITY_THRESHOLD, LOCK_SCREEN_HOLD_S; print('config OK')"
```

Expected: `config OK`

- [ ] **Step 3: Commit**

```bash
git add config.py
git commit -m "feat: add dual-hand gesture threshold constants to config"
```

---

## Task 2: Add keyboard methods and double_click to MouseActuator

**Files:**
- Modify: `core/actuator.py`

- [ ] **Step 1: Add pynput keyboard import at top of file**

After the existing `from pynput.mouse import Button, Controller as MouseController` line, add:

```python
from pynput.keyboard import Controller as KeyboardController, Key
```

- [ ] **Step 2: Add keyboard controller to `__init__`**

In `MouseActuator.__init__`, after `self._dragging = False`, add:

```python
        self._keyboard = KeyboardController()
```

- [ ] **Step 3: Add all new methods after the existing `scroll` method**

```python
    def double_click(self) -> None:
        self._pynput.click(Button.left, 2)

    def win_d(self) -> None:
        with self._keyboard.pressed(Key.cmd):
            self._keyboard.press('d')
            self._keyboard.release('d')

    def alt_tab(self) -> None:
        with self._keyboard.pressed(Key.alt):
            self._keyboard.press(Key.tab)
            self._keyboard.release(Key.tab)

    def win_tab(self) -> None:
        with self._keyboard.pressed(Key.cmd):
            self._keyboard.press(Key.tab)
            self._keyboard.release(Key.tab)

    def win_key(self) -> None:
        self._keyboard.press(Key.cmd)
        self._keyboard.release(Key.cmd)

    def alt_left(self) -> None:
        with self._keyboard.pressed(Key.alt):
            self._keyboard.press(Key.left)
            self._keyboard.release(Key.left)

    def win_l(self) -> None:
        with self._keyboard.pressed(Key.cmd):
            self._keyboard.press('l')
            self._keyboard.release('l')

    def win_snap_left(self) -> None:
        with self._keyboard.pressed(Key.cmd):
            self._keyboard.press(Key.left)
            self._keyboard.release(Key.left)

    def win_snap_right(self) -> None:
        with self._keyboard.pressed(Key.cmd):
            self._keyboard.press(Key.right)
            self._keyboard.release(Key.right)

    def ctrl_down(self) -> None:
        self._keyboard.press(Key.ctrl)

    def ctrl_up(self) -> None:
        self._keyboard.release(Key.ctrl)

    def zoom_in(self) -> None:
        with self._keyboard.pressed(Key.ctrl):
            self._keyboard.press('=')
            self._keyboard.release('=')

    def zoom_out(self) -> None:
        with self._keyboard.pressed(Key.ctrl):
            self._keyboard.press('-')
            self._keyboard.release('-')
```

- [ ] **Step 4: Verify actuator imports and instantiates cleanly**

```powershell
.\.venv\Scripts\python.exe -c "
from core.display import build_virtual_desktop
from core.actuator import MouseActuator
d = build_virtual_desktop()
a = MouseActuator(d.total_width, d.total_height)
print('double_click:', hasattr(a, 'double_click'))
print('win_d:', hasattr(a, 'win_d'))
print('zoom_in:', hasattr(a, 'zoom_in'))
print('actuator OK')
"
```

Expected: all `True`, then `actuator OK`

- [ ] **Step 5: Commit**

```bash
git add core/actuator.py
git commit -m "feat: add keyboard shortcut and double_click methods to MouseActuator"
```

---

## Task 3: Update tracker.py — HandsResult + dual-hand detection

**Files:**
- Modify: `core/tracker.py`

- [ ] **Step 1: Add `HandsResult` dataclass after the `Landmark` dataclass**

```python
@dataclass
class HandsResult:
    """Holds landmarks for both hands. None = that hand not detected this frame."""
    left: list[Landmark] | None = None   # user's left hand (21 landmarks)
    right: list[Landmark] | None = None  # user's right hand (21 landmarks)
```

- [ ] **Step 2: Update `HandTracker.__init__` — set `num_hands=2`**

Change `num_hands=MP_MAX_HANDS` to `num_hands=2` in the `HandLandmarkerOptions` block:

```python
        options = HandLandmarkerOptions(
            base_options=base_options,
            running_mode=RunningMode.IMAGE,
            num_hands=2,
            min_hand_detection_confidence=MP_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=MP_TRACKING_CONFIDENCE,
            min_tracking_confidence=MP_TRACKING_CONFIDENCE,
        )
```

Also update the log message:

```python
        logger.info("MediaPipe HandLandmarker initialized (max_hands=2)")
```

- [ ] **Step 3: Replace `process()` return type and body**

Replace the entire `process` method:

```python
    def process(self, frame: np.ndarray) -> HandsResult:
        """
        Process one BGR frame. Always returns HandsResult (never None).
        Each field is None if that hand was not detected.

        MediaPipe 'Left' from camera perspective = user's Right hand (mirrored).
        """
        result_obj = HandsResult()
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self._detector.detect(mp_image)
        except Exception as e:
            logger.warning("MediaPipe processing error: %s", e)
            return result_obj

        if not result.hand_landmarks:
            return result_obj

        for i, hand_lms in enumerate(result.hand_landmarks):
            landmarks = [
                Landmark(
                    x=lm.x,
                    y=lm.y,
                    z=lm.z,
                    visibility=getattr(lm, "visibility", None) or 0.0,
                )
                for lm in hand_lms
            ]
            # Flip: camera "Left" = user's right hand (webcam is a mirror)
            cam_label = result.handedness[i][0].category_name
            if cam_label == "Left":
                result_obj.right = landmarks
            else:
                result_obj.left = landmarks

        return result_obj
```

- [ ] **Step 4: Update `MP_MAX_HANDS` import — it's no longer used in tracker, remove it**

Change the import line from:

```python
from config import MP_MAX_HANDS, MP_DETECTION_CONFIDENCE, MP_TRACKING_CONFIDENCE, MP_MODEL_PATH
```

to:

```python
from config import MP_DETECTION_CONFIDENCE, MP_TRACKING_CONFIDENCE, MP_MODEL_PATH
```

- [ ] **Step 5: Verify tracker returns HandsResult**

```powershell
.\.venv\Scripts\python.exe -c "
from core.tracker import HandTracker, HandsResult
t = HandTracker()
print('HandsResult:', HandsResult)
print('process signature:', t.process.__annotations__)
t.close()
print('tracker OK')
"
```

Expected: `HandsResult` class printed, `process` shows return annotation, `tracker OK`

- [ ] **Step 6: Commit**

```bash
git add core/tracker.py
git commit -m "feat: add HandsResult dataclass and dual-hand tracking to HandTracker"
```

---

## Task 4: Create core/gestures/ package — utils + skeleton

**Files:**
- Create: `core/gestures/__init__.py`
- Create: `core/gestures/utils.py`

- [ ] **Step 1: Create `core/gestures/utils.py` with shared helpers**

```python
# core/gestures/utils.py
"""Shared landmark geometry helpers used by all gesture processors."""

import numpy as np
from core.tracker import Landmark


def dist3d(a: Landmark, b: Landmark) -> float:
    """3D Euclidean distance in normalized MediaPipe coordinate space."""
    return float(np.linalg.norm([a.x - b.x, a.y - b.y, a.z - b.z]))


def is_extended(tip: Landmark, pip: Landmark) -> bool:
    """Finger extended = tip is above (lower y) its PIP joint. MediaPipe y=0 is top."""
    return tip.y < pip.y


def is_curled(tip: Landmark, pip: Landmark) -> bool:
    return tip.y > pip.y


def is_fist(lm: list[Landmark]) -> bool:
    """All 5 fingers curled."""
    return (
        is_curled(lm[8],  lm[6])   # index
        and is_curled(lm[12], lm[10])  # middle
        and is_curled(lm[16], lm[14])  # ring
        and is_curled(lm[20], lm[18])  # pinky
        and is_curled(lm[4],  lm[2])   # thumb (tip vs MCP)
    )


def is_peace_sign(lm: list[Landmark]) -> bool:
    """Index + middle extended, thumb + ring + pinky curled."""
    return (
        is_extended(lm[8],  lm[6])    # index extended
        and is_extended(lm[12], lm[10])   # middle extended
        and is_curled(lm[16],  lm[14])   # ring curled
        and is_curled(lm[20],  lm[18])   # pinky curled
        and is_curled(lm[4],   lm[2])    # thumb curled (prevents conflict with open hand)
    )


def is_open_palm(lm: list[Landmark]) -> bool:
    """All 5 fingers extended."""
    return (
        is_extended(lm[8],  lm[6])
        and is_extended(lm[12], lm[10])
        and is_extended(lm[16], lm[14])
        and is_extended(lm[20], lm[18])
        and is_extended(lm[4],  lm[2])
    )


def is_v_sign(lm: list[Landmark]) -> bool:
    """Index + middle extended, ring + pinky curled (thumb free)."""
    return (
        is_extended(lm[8],  lm[6])
        and is_extended(lm[12], lm[10])
        and is_curled(lm[16],  lm[14])
        and is_curled(lm[20],  lm[18])
    )


def is_four_fingers(lm: list[Landmark]) -> bool:
    """Index + middle + ring + pinky extended, thumb curled."""
    return (
        is_extended(lm[8],  lm[6])
        and is_extended(lm[12], lm[10])
        and is_extended(lm[16], lm[14])
        and is_extended(lm[20], lm[18])
        and is_curled(lm[4],   lm[2])
    )
```

- [ ] **Step 2: Create placeholder `core/gestures/__init__.py`**

```python
# core/gestures/__init__.py
from core.gestures.orchestrator import GestureOrchestrator

__all__ = ["GestureOrchestrator"]
```

- [ ] **Step 3: Verify utils imports**

```powershell
.\.venv\Scripts\python.exe -c "from core.gestures.utils import dist3d, is_fist, is_peace_sign; print('utils OK')"
```

Expected: `utils OK`

- [ ] **Step 4: Commit**

```bash
git add core/gestures/__init__.py core/gestures/utils.py
git commit -m "feat: create gestures package skeleton and shared geometry utils"
```

---

## Task 5: Create right_hand.py — full right-hand state machine

**Files:**
- Create: `core/gestures/right_hand.py`

- [ ] **Step 1: Create `core/gestures/right_hand.py`**

```python
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
```

- [ ] **Step 2: Verify import**

```powershell
.\.venv\Scripts\python.exe -c "from core.gestures.right_hand import RightHandProcessor; print('right_hand OK')"
```

Expected: `right_hand OK`

- [ ] **Step 3: Commit**

```bash
git add core/gestures/right_hand.py
git commit -m "feat: implement RightHandProcessor with thumb-pinch clicks, peace-sign wrist scroll, fist lock"
```

---

## Task 6: Create left_hand.py — Windows system shortcuts

**Files:**
- Create: `core/gestures/left_hand.py`

- [ ] **Step 1: Create `core/gestures/left_hand.py`**

```python
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
```

- [ ] **Step 2: Verify import**

```powershell
.\.venv\Scripts\python.exe -c "from core.gestures.left_hand import LeftHandProcessor; print('left_hand OK')"
```

Expected: `left_hand OK`

- [ ] **Step 3: Commit**

```bash
git add core/gestures/left_hand.py
git commit -m "feat: implement LeftHandProcessor with Windows system shortcuts"
```

---

## Task 7: Create two_hand.py — zoom, snap, lock screen

**Files:**
- Create: `core/gestures/two_hand.py`

- [ ] **Step 1: Create `core/gestures/two_hand.py`**

```python
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
```

- [ ] **Step 2: Verify import**

```powershell
.\.venv\Scripts\python.exe -c "from core.gestures.two_hand import TwoHandProcessor; print('two_hand OK')"
```

Expected: `two_hand OK`

- [ ] **Step 3: Commit**

```bash
git add core/gestures/two_hand.py
git commit -m "feat: implement TwoHandProcessor with zoom, snap, and lock-screen gestures"
```

---

## Task 8: Create orchestrator.py and wire the package

**Files:**
- Create: `core/gestures/orchestrator.py`
- Update: `core/gestures/__init__.py` (already imports from orchestrator — just verify)

- [ ] **Step 1: Create `core/gestures/orchestrator.py`**

```python
# core/gestures/orchestrator.py
"""
GestureOrchestrator — routes HandsResult to per-hand processors.

Exposes process(hands: HandsResult) as a drop-in replacement for
the old GestureProcessor.process(landmarks: list[Landmark]).
"""

import logging

from core.tracker import HandsResult
from core.display import VirtualDesktop, TrackpadZone
from core.actuator import MouseActuator
from core.gestures.right_hand import RightHandProcessor
from core.gestures.left_hand import LeftHandProcessor
from core.gestures.two_hand import TwoHandProcessor

logger = logging.getLogger(__name__)


class GestureOrchestrator:
    """
    Coordinates right, left, and two-hand processors.

    Args:
        actuator: MouseActuator instance
        desktop:  VirtualDesktop for coordinate mapping
        trackpad: TrackpadZone for coordinate mapping
    """

    def __init__(
        self,
        actuator: MouseActuator,
        desktop: VirtualDesktop,
        trackpad: TrackpadZone,
    ) -> None:
        self._right = RightHandProcessor(actuator, desktop, trackpad)
        self._left = LeftHandProcessor(actuator)
        self._two = TwoHandProcessor(actuator)
        logger.info("GestureOrchestrator ready (dual-hand mode)")

    def process(self, hands: HandsResult) -> None:
        """Process one frame. Call once per frame regardless of hand visibility."""
        self._right.process(hands.right)

        if hands.left is not None:
            self._left.process(hands.left)
        else:
            self._left.process(None)

        if hands.left is not None and hands.right is not None:
            self._two.process(hands.left, hands.right)
```

- [ ] **Step 2: Verify full package import**

```powershell
.\.venv\Scripts\python.exe -c "
from core.gestures import GestureOrchestrator
from core.tracker import HandsResult
from core.display import build_virtual_desktop, build_trackpad_zone
from core.actuator import MouseActuator
d = build_virtual_desktop()
t = build_trackpad_zone()
a = MouseActuator(d.total_width, d.total_height)
orch = GestureOrchestrator(a, d, t)
# Feed empty HandsResult (no hands)
orch.process(HandsResult())
print('orchestrator OK')
"
```

Expected: `GestureOrchestrator ready (dual-hand mode)` log line, then `orchestrator OK`

- [ ] **Step 3: Commit**

```bash
git add core/gestures/orchestrator.py core/gestures/__init__.py
git commit -m "feat: implement GestureOrchestrator routing HandsResult to sub-processors"
```

---

## Task 9: Delete old gestures.py and update main.py

**Files:**
- Delete: `core/gestures.py`
- Modify: `main.py`

- [ ] **Step 1: Delete `core/gestures.py`**

```powershell
Remove-Item "C:\Users\Lenovo\Desktop\Code\2026\AirMouse_AI\core\gestures.py"
```

Verify gone:

```powershell
Test-Path "C:\Users\Lenovo\Desktop\Code\2026\AirMouse_AI\core\gestures.py"
```

Expected: `False`

- [ ] **Step 2: Update `main.py` — swap import**

Change line 36:

```python
from core.gestures import GestureProcessor
```

to:

```python
from core.gestures import GestureOrchestrator
```

- [ ] **Step 3: Update `main.py` — swap instantiation**

Change line 165:

```python
        processor = GestureProcessor(actuator, desktop, trackpad)
```

to:

```python
        processor = GestureOrchestrator(actuator, desktop, trackpad)
```

- [ ] **Step 4: Update `main.py` — remove `if landmarks is not None` guard**

Replace the block:

```python
                landmarks = tracker.process(frame)

                if landmarks is not None:
                    processor.process(landmarks)
```

with:

```python
                hands = tracker.process(frame)
                processor.process(hands)
```

- [ ] **Step 5: Run smoke test**

```powershell
.\.venv\Scripts\python.exe test_startup.py 2>&1 | Select-String "\[PASS\]|\[FAIL\]|passed"
```

Expected:

```
[PASS] Display geometry
[PASS] Camera open + frame read
[PASS] MediaPipe HandTracker init
[PASS] MouseActuator move(0,0)
4/4 passed
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: wire GestureOrchestrator into main loop; remove old gestures.py"
```

---

## Task 10: Update test_startup.py for new API + run end-to-end

**Files:**
- Modify: `test_startup.py`

- [ ] **Step 1: Update `test_actuator` in `test_startup.py` to use `GestureOrchestrator`**

Replace the existing `test_actuator` function:

```python
def test_actuator() -> None:
    from core.display import build_virtual_desktop, build_trackpad_zone
    from core.actuator import MouseActuator
    from core.gestures import GestureOrchestrator
    from core.tracker import HandsResult
    desktop = build_virtual_desktop()
    trackpad = build_trackpad_zone()
    actuator = MouseActuator(desktop.total_width, desktop.total_height)
    orch = GestureOrchestrator(actuator, desktop, trackpad)
    # Feed empty frame (no hands) — verifies orchestrator initialises and processes without error
    orch.process(HandsResult())
    # Also verify raw move still works
    actuator.move(0, 0)
```

- [ ] **Step 2: Run updated smoke test**

```powershell
.\.venv\Scripts\python.exe test_startup.py 2>&1 | Select-String "\[PASS\]|\[FAIL\]|passed"
```

Expected: `4/4 passed`

- [ ] **Step 3: Start main.py and verify startup logs**

```powershell
$proc = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "main.py" -PassThru -NoNewWindow -RedirectStandardOutput ".\o.txt" -RedirectStandardError ".\e.txt"
Start-Sleep -Seconds 10
$proc.Kill()
Get-Content ".\o.txt",".\e.txt" -ErrorAction SilentlyContinue | Select-String "\[INFO\]"
Remove-Item ".\o.txt",".\e.txt" -ErrorAction SilentlyContinue
```

Expected log lines (all must appear):

```
[INFO] core.actuator: MouseActuator ready
[INFO] core.camera: Camera opened: 1280x720 @ 60.0 fps
[INFO] core.tracker: MediaPipe HandLandmarker initialized (max_hands=2)
[INFO] core.gestures.orchestrator: GestureOrchestrator ready (dual-hand mode)
[INFO] airmouse.main: Running. Press Ctrl+C to exit.
[INFO] airmouse.main: FPS: ...
```

- [ ] **Step 4: Commit final state**

```bash
git add test_startup.py
git commit -m "test: update smoke test for GestureOrchestrator and HandsResult API"
```

---

## Manual Gesture Checklist (run with app live after all tasks complete)

Test these in order with the app running:

- [ ] Right fist → cursor freezes, no clicks fire
- [ ] Open right fist → cursor resumes tracking index tip
- [ ] Thumb+index pinch + release → left click fires
- [ ] Thumb+index pinch twice quickly → double click fires
- [ ] Thumb+index pinch + hold 0.4s → drag mode activates, cursor drags
- [ ] Release pinch during drag → drag ends
- [ ] Thumb+middle pinch → right click fires
- [ ] Peace sign (index+middle up, others curled) → scroll mode (cursor stops)
- [ ] Peace sign + wrist flick up → content scrolls up
- [ ] Peace sign + wrist flick down → content scrolls down
- [ ] Peace sign + fast flick → more scroll ticks than slow flick
- [ ] Open hand from peace sign → cursor resumes
- [ ] Left open palm → desktop shown (Win+D)
- [ ] Left V-sign → Alt+Tab fires
- [ ] Left four fingers → Task View opens (Win+Tab)
- [ ] Left fist held → Ctrl held (right-hand click = Ctrl+Click for multi-select)
- [ ] Left fist released → Ctrl released
- [ ] Both fists held 1s → screen locks (Win+L) — **caution: locks screen**
