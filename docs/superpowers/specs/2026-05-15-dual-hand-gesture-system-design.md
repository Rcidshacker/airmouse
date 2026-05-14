# AirMouse AI — Dual-Hand AVP-Style Gesture System Design

**Date:** 2026-05-15
**Status:** Approved
**Goal:** Replace the current index-middle-finger gesture set with a thumb-trigger, dual-hand, wrist-scroll gesture system inspired by Apple Vision Pro interaction philosophy.

---

## Problem Statement

The current gesture system has three fundamental flaws:

1. **False click triggers** — index+middle pinch fires during scroll attempts because both fingers are extended in similar positions
2. **Ambiguous right-click** — index+ring is anatomically difficult; users cannot reliably trigger it
3. **No rest state** — no way to park the hand without the cursor moving

The redesign eliminates all three by: (a) making thumb the exclusive trigger, (b) replacing finger-extension scroll with wrist-velocity scroll, (c) adding fist = lock mode.

---

## Architecture

```
tracker.py          →  HandsResult(left: list[Landmark] | None, right: list[Landmark] | None)
gestures/
  orchestrator.py   →  routes landmarks to each processor, handles two-hand logic
  right_hand.py     →  cursor + thumb-pinch clicks + peace-sign wrist scroll + fist lock
  left_hand.py      →  Windows system shortcuts (optional layer)
  two_hand.py       →  zoom, snap, lock screen
config.py           →  all new thresholds
main.py             →  no changes (uses GestureOrchestrator same interface as old GestureProcessor)
```

The orchestrator exposes the same `process(landmarks)` interface as the old `GestureProcessor` — except it accepts a `HandsResult` instead of a flat list. `main.py` passes `HandsResult` directly.

---

## Gesture Definitions

### Right Hand (always active)

| Gesture | Trigger | Action | Notes |
|---------|---------|--------|-------|
| Cursor move | Index tip position, hand open | Mouse move | Only when not in LOCKED state |
| Left click | Thumb + Index tip distance < `THUMB_INDEX_CLICK_DIST` | `left_click()` | Release fires click (same state machine as before) |
| Double click | Two thumb+index pinches within `DOUBLE_CLICK_WINDOW_S` | `double_click()` via two rapid clicks |  |
| Drag | Thumb+Index pinch held ≥ `DRAG_HOLD_SECONDS` | `drag_start()` → `drag_end()` on release | Cursor tracks during drag |
| Right click | Thumb + Middle tip distance < `THUMB_MIDDLE_CLICK_DIST` | `right_click()` | Cooldown applies |
| Scroll mode | Peace sign: index+middle extended, thumb+ring+pinky curled | Enters SCROLLING state | Cursor movement suspended |
| Scroll up | SCROLLING state + wrist Y velocity < `-WRIST_VELOCITY_THRESHOLD` | `scroll(ticks)` | Ticks = clamp(1, 5, velocity_magnitude / SCROLL_TICK_SCALE) |
| Scroll down | SCROLLING state + wrist Y velocity > `+WRIST_VELOCITY_THRESHOLD` | `scroll(-ticks)` | Same speed scaling |
| Lock | All 5 fingers curled (fist) | LOCKED state | No cursor movement, no gestures fire |
| Unlock | Fist released (any finger extends) | Returns to IDLE | |

**Peace sign definition:**
- `lm[8].y < lm[6].y` (index extended)
- `lm[12].y < lm[10].y` (middle extended)
- `lm[16].y > lm[14].y` (ring curled)
- `lm[20].y > lm[18].y` (pinky curled)
- `lm[4].y > lm[2].y` (thumb curled — prevents conflict with cursor-pointing hand)

**Fist definition:**
- All 4 fingers curled: index, middle, ring, pinky tips below their PIP joints
- Thumb tip below MCP: `lm[4].y > lm[2].y`

**Wrist velocity:** Computed as `(wrist_y_now - wrist_y_prev) / dt` on landmark 0. Negative = hand moved up = scroll up (MediaPipe y=0 is top).

### Right Hand State Machine

```
IDLE
  ├─ fist detected          → LOCKED
  ├─ peace sign detected    → SCROLLING
  └─ thumb+index pinch      → LEFT_PINCH_PENDING_DRAG

LOCKED
  └─ any finger extends     → IDLE

SCROLLING
  ├─ wrist velocity ↑       → emit scroll(+ticks)  [stay SCROLLING]
  ├─ wrist velocity ↓       → emit scroll(-ticks)  [stay SCROLLING]
  └─ peace sign released    → IDLE

LEFT_PINCH_PENDING_DRAG
  ├─ pinch released < DRAG_HOLD_SECONDS   → emit left_click() → IDLE
  └─ pinch held ≥ DRAG_HOLD_SECONDS       → drag_start() → DRAGGING

DRAGGING
  └─ pinch released         → drag_end() → IDLE
```

### Left Hand (optional — absence does not break right-hand behavior)

Detection: if `hands_result.left is None`, left-hand processor is skipped entirely.

| Gesture | Trigger | Windows Action |
|---------|---------|----------------|
| Show Desktop | Open palm facing camera (all 5 extended) | `Win+D` |
| Window Switch | V-sign (index+middle extended, others curled) | `Alt+Tab` (hold V = keep switcher open) |
| Task View | 4 fingers extended (index+middle+ring+pinky), thumb curled | `Win+Tab` |
| Start Menu | Left thumb+index pinch | `Win` key |
| Ctrl modifier | Left fist held | Holds `Ctrl` key down; right-hand click = `Ctrl+Click` |
| Go Back | Left index pointing + swipe right (wrist x velocity > threshold) | `Alt+Left` |

### Two-Hand Gestures

Both hands must be tracked. Orchestrator checks for two-hand conditions after individual processors run.

| Gesture | Trigger | Action |
|---------|---------|--------|
| Zoom in | Both hands in thumb+index pinch, distance between wrists increases | `Ctrl++` per threshold cross |
| Zoom out | Both hands in thumb+index pinch, distance between wrists decreases | `Ctrl+-` per threshold cross |
| Lock screen | Both fists held ≥ `LOCK_SCREEN_HOLD_S` (1.0s) | `Win+L` |
| Snap left | Left open palm held + right fist swipe left | `Win+Left` |
| Snap right | Left open palm held + right fist swipe right | `Win+Right` |

---

## File Map

| File | Change |
|------|--------|
| `core/tracker.py` | Add `HandsResult` dataclass; set `num_hands=2`; parse `result.handedness` to assign left/right; return `HandsResult` |
| `core/gestures/__init__.py` | New package init, exports `GestureOrchestrator` |
| `core/gestures/orchestrator.py` | Coordinates right, left, two-hand processors; exposes `process(hands: HandsResult)` |
| `core/gestures/right_hand.py` | Full right-hand state machine (cursor, clicks, scroll, lock) |
| `core/gestures/left_hand.py` | Left-hand system shortcut detection |
| `core/gestures/two_hand.py` | Two-hand zoom/snap/lock detection |
| `core/gestures.py` | Deleted (replaced by package) |
| `config.py` | Add new threshold constants; keep old ones until migration complete |
| `main.py` | Update import from `GestureProcessor` → `GestureOrchestrator`; pass `HandsResult` |

---

## New Config Constants

```python
# ── Thumb-pinch thresholds (normalized MediaPipe coords) ──────────────────────
THUMB_INDEX_CLICK_DIST  = 0.045   # thumb tip ↔ index tip
THUMB_MIDDLE_CLICK_DIST = 0.050   # thumb tip ↔ middle tip (slightly looser)

# ── Fist detection ────────────────────────────────────────────────────────────
FIST_CURL_THRESHOLD = 0.0         # all finger tips must be below their PIP joints

# ── Wrist scroll ──────────────────────────────────────────────────────────────
WRIST_VELOCITY_THRESHOLD = 0.008  # normalized units/ms — minimum flick to register
SCROLL_TICK_SCALE        = 0.003  # velocity / scale = tick count (clamped 1–5)
SCROLL_COOLDOWN_S        = 0.12   # minimum gap between scroll emissions

# ── Two-hand ──────────────────────────────────────────────────────────────────
ZOOM_WRIST_DELTA         = 0.05   # normalized wrist distance change to trigger zoom tick
LOCK_SCREEN_HOLD_S       = 1.0    # both fists held duration to trigger Win+L

# ── Double click ──────────────────────────────────────────────────────────────
DOUBLE_CLICK_WINDOW_S    = 0.4    # max time between two pinches for double-click
```

---

## MediaPipe Handedness Note

MediaPipe `handedness[i].category_name` returns `"Left"` or `"Right"` from the **camera's perspective** (mirror of user). Must flip: camera `"Left"` = user's right hand, camera `"Right"` = user's left hand.

```python
cam_label = result.handedness[i][0].category_name  # "Left" or "Right"
user_label = "right" if cam_label == "Left" else "left"
```

---

## Wrist Velocity Implementation

```python
# In RightHandProcessor, per frame:
wrist_y = landmarks[0].y          # landmark 0 = wrist
dt = now - self._last_frame_time  # seconds
if dt > 0:
    velocity_y = (wrist_y - self._prev_wrist_y) / dt
self._prev_wrist_y = wrist_y
self._last_frame_time = now
# Negative velocity = hand moved up (MediaPipe y=0 is top) = scroll up
```

---

## Testing

`test_startup.py` smoke test updated to instantiate `GestureOrchestrator` instead of old `GestureProcessor`. No camera or hand required for init test.

New manual test checklist (run with app live):
- [ ] Right fist → cursor freezes
- [ ] Open fist → cursor resumes
- [ ] Thumb+index pinch → left click fires on release
- [ ] Thumb+index hold 0.4s → drag mode activates
- [ ] Thumb+middle pinch → right click
- [ ] Peace sign + wrist flick up → scroll up
- [ ] Peace sign + wrist flick down → scroll down
- [ ] Peace sign faster flick → more scroll ticks
- [ ] Left open palm → Win+D
- [ ] Left V-sign → Alt+Tab
- [ ] Both fists 1s → Win+L

---

## Out of Scope

- Eye tracking (no hardware)
- Gesture customization UI
- Per-app gesture profiles
- Voice + gesture combos
