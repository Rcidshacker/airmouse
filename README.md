# AI Air Mouse

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13+-blue.svg" alt="Python 3.13+">
  <img src="https://img.shields.io/badge/Windows-10%2F11-0078D6.svg" alt="Windows 10/11">
  <img src="https://img.shields.io/badge/MediaPipe-0.10.35-green.svg" alt="MediaPipe 0.10.35">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/Platform-x86__64-lightgrey.svg" alt="x86_64">
</p>

<p align="center">
  <b>Dual-hand gesture-controlled virtual mouse for Windows.</b><br>
  Move, click, drag, scroll, and trigger system shortcuts — no touch, no hardware, just your hands.
</p>

---

AI Air Mouse turns your webcam into a two-hand gesture controller modelled after Apple Vision Pro's interaction philosophy. The right hand controls the cursor and fires actions via thumb-pinch. The left hand triggers Windows system shortcuts. Together they enable zoom, window snapping, and screen lock. Everything runs on-device with zero cloud dependencies.

## Features

### Right Hand (always active)
- **Cursor tracking** — Index fingertip mapped to screen coordinates via the [1-euro filter](https://cristal.univ-lille.fr/~casiez/1euro/) for jitter-free, lag-free movement
- **Left click** — Thumb + index fingertip pinch (tap and release)
- **Double click** — Two thumb+index pinches within 0.4 s
- **Right click** — Thumb + middle fingertip pinch
- **Drag & drop** — Hold thumb+index pinch for 0.4 s → drag activates; release to drop
- **Scroll mode** — Peace sign (index + middle extended, others curled) → wrist flick to scroll; faster flick = more ticks (1–5)
- **Cursor lock** — Fist gesture freezes cursor; open hand to resume

### Left Hand (optional system layer)
| Gesture | Action |
|---------|--------|
| Open palm | Win+D (Show Desktop) |
| V-sign (index + middle up) | Alt+Tab (cycle windows) |
| Four fingers up | Win+Tab (Task View) |
| Thumb + index pinch | Win key (Start Menu) |
| Fist held | Ctrl modifier (held until released) |
| Index pointing + wrist swipe right | Alt+Left (Go Back) |

### Two-Hand Gestures
| Gesture | Action |
|---------|--------|
| Both hands pinch + spread wrists | Ctrl+= (Zoom In) |
| Both hands pinch + close wrists | Ctrl+− (Zoom Out) |
| Left open palm + right fist swipe | Win+Left / Win+Right (Snap) |
| Both fists held 1 s | Win+L (Lock Screen) |

### System
- **Multi-monitor support** — DPI-aware virtual desktop spanning all connected displays
- **Async capture** — Dedicated daemon thread for non-blocking frame reads at native webcam FPS
- **Windows real-time tuning** — 1 ms timer resolution, `HIGH_PRIORITY_CLASS`, MMCSS "Games" registration, pointer acceleration suppression

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.12 | 3.13 |
| Windows | 10 | 11 |
| Webcam | Any DirectShow-compatible camera | 60 FPS capable |
| RAM | 2 GB | 4 GB+ |

Administrator access is recommended (not required) for process priority elevation and MMCSS registration.

## Quick Start

```bash
git clone https://github.com/Rcidshacker/airmouse.git
cd airmouse
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python main.py
```

Press **Ctrl+C** to exit. All system settings are automatically restored on shutdown.

## Calibration

All tunable parameters live in `config.py`.

| Symptom | Parameter | Direction |
|---------|-----------|-----------|
| Cursor jittery at rest | `ONE_EURO_MINCUTOFF` | Decrease (try 0.3) |
| Cursor lags during fast motion | `ONE_EURO_BETA` | Increase (try 0.05) |
| Left click not triggering | `THUMB_INDEX_CLICK_DIST` | Increase (try 0.055) |
| Accidental left clicks | `THUMB_INDEX_CLICK_DIST` | Decrease (try 0.04) |
| Right click not triggering | `THUMB_MIDDLE_CLICK_DIST` | Increase |
| Scroll too sensitive | `WRIST_VELOCITY_THRESHOLD` | Increase |
| Drag too sensitive | `DRAG_HOLD_SECONDS` | Increase (try 0.5) |
| Zoom fires too easily | `ZOOM_WRIST_DELTA` | Increase (try 0.07) |
| Low FPS | `CAMERA_WIDTH` / `CAMERA_HEIGHT` | Reduce to 640×480 |

## Architecture

```
main.py                              Entry point + Windows OS tuning + inference loop
  |
  +-- core/camera.py                 Async frame capture (daemon thread, DirectShow)
  +-- core/tracker.py                MediaPipe HandLandmarker wrapper → HandsResult
  +-- core/gestures/
  |     +-- orchestrator.py          Routes HandsResult to per-hand processors
  |     +-- right_hand.py            Cursor + thumb-pinch clicks + peace-sign scroll + fist lock
  |     +-- left_hand.py             Windows system shortcuts (Win+D, Alt+Tab, Ctrl, …)
  |     +-- two_hand.py              Zoom / snap / lock-screen
  |     +-- utils.py                 Shared geometry: dist3d, is_fist, is_peace_sign, …
  |
  +-- core/filter.py                 1-euro filter (Casiez et al., CHI 2012)
  +-- core/display.py                Multi-monitor DPI-aware coordinate mapping
  +-- core/actuator.py               Windows SendInput + pynput mouse/keyboard injection
  +-- config.py                      Single source of truth for all tunables
```

### Key Design Decisions

- **Thumb as exclusive trigger**: Every click, right-click, and drag is fired by the thumb. Index stays as pointer; no ambiguous two-finger combinations.
- **Wrist velocity for scroll**: Peace-sign posture + wrist flick avoids the anatomically awkward "extend pinky" scroll. Velocity magnitude maps directly to tick count.
- **Fist = rest state**: Fist freezes the cursor so users can lower their hand without phantom movement. No accidental clicks while resting.
- **SendInput over `mouse_event`**: `mouse_event` is deprecated since Vista; SendInput is the documented low-overhead replacement.
- **SendInput for movement, pynput for clicks**: pynput wraps SendInput internally, so direct ctypes for movement eliminates one layer. pynput is retained for click/drag and keyboard because its press/release abstraction is cleaner than manual flag management.
- **DirectShow over MSMF**: DirectShow (`CAP_DSHOW`) provides lower capture latency than Media Foundation on Windows.
- **1-euro filter over Kalman**: Speed-dependent adaptive low-pass filter that strictly outperforms Kalman for 2D cursor trajectories (Casiez et al., CHI 2012).
- **MediaPipe handedness flip**: MediaPipe reports handedness from the camera's perspective. A camera-"Left" hand is the user's right (webcam is a mirror), so the tracker flips the label before returning `HandsResult`.

## Project Structure

```
airmouse/
├── main.py              Entry point, Windows OS setup, main inference loop
├── config.py            All tunable parameters (single source of truth)
├── requirements.txt     Dependencies
├── test_startup.py      Smoke tests for each subsystem
├── models/              MediaPipe hand_landmarker.task model bundle (git-ignored)
└── core/
    ├── camera.py        Asynchronous frame capture via daemon thread
    ├── filter.py        1-euro filter (Casiez et al. 2012)
    ├── display.py       Multi-monitor virtual desktop mapping, DPI awareness
    ├── tracker.py       MediaPipe HandLandmarker → HandsResult (dual-hand)
    ├── actuator.py      Windows SendInput + pynput mouse and keyboard actuation
    └── gestures/
        ├── orchestrator.py   GestureOrchestrator — top-level coordinator
        ├── right_hand.py     RightHandProcessor — cursor, clicks, scroll, lock
        ├── left_hand.py      LeftHandProcessor — Windows shortcuts
        ├── two_hand.py       TwoHandProcessor — zoom, snap, lock-screen
        └── utils.py          Shared landmark geometry helpers
```

## Troubleshooting

**Camera fails to open** — Check Device Manager. Try `CAMERA_INDEX = 1` or `2` for multi-camera setups.

**Cursor maps to wrong positions** — The app sets `PROCESS_PER_MONITOR_DPI_AWARE` at startup. If DPI scaling is mixed across monitors, set all to 100% or 125% for testing.

**Low FPS** — Close other apps using the webcam. MediaPipe dual-hand tracking is heavier than single-hand; ~30 FPS at 1280×720 is normal. Reduce to 640×480 if needed.

**Gestures not recognized** — Ensure good, even lighting. Keep your hand 40–70 cm from the camera. Adjust the relevant threshold in `config.py`.

**Permission warnings** — `HIGH_PRIORITY_CLASS` and MMCSS need Administrator privileges. The app still works without elevation but may drop frames under system load.

## License

[MIT License](LICENSE)
