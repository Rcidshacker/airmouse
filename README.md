<div align="center">

# AI Air Mouse

### Control your PC with nothing but your hands.

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com/windows)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.35-00897B?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/edge/mediapipe)
[![License](https://img.shields.io/badge/License-MIT-F7CA18?style=for-the-badge)](LICENSE)

**No mouse. No touchpad. No hardware. Just a webcam.**

[Getting Started](#-quick-start) · [Gesture Guide](#-gesture-guide) · [Calibration](#-calibration) · [Architecture](#-architecture) · [Troubleshooting](#-troubleshooting)

</div>

---

## What is this?

AI Air Mouse uses your webcam and [MediaPipe's hand landmark model](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker) to track your hands in real time and translate gestures into mouse and keyboard actions — entirely on your device, with zero cloud calls.

The interaction model is inspired by **Apple Vision Pro**: your thumb is always the trigger, your index finger is always the pointer, and there are no ambiguous multi-finger combinations. The right hand owns the mouse; the left hand optionally controls Windows system shortcuts. Together they support clicks, drag, scroll, zoom, window snapping, and more.

```
Webcam → MediaPipe (21 landmarks per hand) → Gesture State Machines → SendInput / pynput → Windows
```

Everything runs in a tight async loop. Frame capture never blocks inference. Cursor smoothing uses the [1-euro filter](https://cristal.univ-lille.fr/~casiez/1euro/) — zero perceptible lag at high speed, zero jitter at rest.

---

## Requirements

| | Minimum | Recommended |
|---|---|---|
| **Python** | 3.12 | 3.13 |
| **Windows** | 10 | 11 |
| **Webcam** | Any DirectShow camera | 60 FPS capable |
| **RAM** | 2 GB | 4 GB+ |
| **Privileges** | Standard user | Administrator (for priority tuning) |

---

## Quick Start

```powershell
git clone https://github.com/Rcidshacker/airmouse.git
cd airmouse

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# Verify all subsystems are healthy
.\.venv\Scripts\python test_startup.py

# Launch
.\.venv\Scripts\python main.py
```

> Press **Ctrl+C** to exit. All Windows settings (timer resolution, pointer acceleration, process priority) are automatically restored on shutdown.

On startup you'll see logs like:

```
[INFO] core.tracker:    MediaPipe HandLandmarker initialized (max_hands=2)
[INFO] core.gestures.orchestrator: GestureOrchestrator ready (dual-hand mode)
[INFO] airmouse.main:   Running. Press Ctrl+C to exit.
[INFO] airmouse.main:   FPS: 31.4
```

---

## Gesture Guide

### Right Hand — Mouse Control

The right hand is always active. Index fingertip drives the cursor.

| Gesture | How to do it | Action |
|---------|-------------|--------|
| **Point** | Index finger extended, others relaxed | Move cursor |
| **Pinch** | Touch thumb tip to index tip, release | Left click |
| **Double pinch** | Two pinches within 0.4 s | Double click |
| **Pinch + hold** | Touch thumb to index, hold 0.4 s | Start drag — release to drop |
| **Thumb + middle** | Touch thumb tip to middle tip | Right click |
| **Peace sign** | Index + middle up, thumb + ring + pinky curled | Enter scroll mode |
| **Wrist flick** | *(while in scroll mode)* flick wrist up/down | Scroll — faster flick = more ticks |
| **Fist** | Close all fingers | Freeze cursor — open hand to resume |

> **Tip:** The fist gesture is your rest state. Drop your hand, make a fist, and nothing will move or click until you extend your fingers again.

---

### Left Hand — System Shortcuts *(optional)*

The left hand adds a system shortcut layer on top of right-hand mouse control. You can ignore it entirely — right-hand behavior is unaffected.

| Gesture | Action |
|---------|--------|
| Open palm (all 5 fingers extended) | `Win+D` — Show Desktop |
| V-sign (index + middle up, others curled) | `Alt+Tab` — Cycle Windows |
| Four fingers (index–pinky up, thumb curled) | `Win+Tab` — Task View |
| Thumb + index pinch | `Win` — Start Menu |
| Fist (held) | Hold `Ctrl` — combine with right-hand click for multi-select |
| Fist (released) | Release `Ctrl` |
| Index pointing + wrist swipe right | `Alt+Left` — Go Back |

> **Ctrl + Click workflow:** Make a left-hand fist to hold Ctrl, then left-click with your right hand to multi-select items. Release the fist to drop Ctrl.

---

### Two-Hand Gestures — Power Actions

Activated only when both hands are visible.

| Gesture | Action |
|---------|--------|
| Both hands pinch + spread wrists apart | `Ctrl+=` — Zoom In |
| Both hands pinch + bring wrists together | `Ctrl+−` — Zoom Out |
| Left open palm + right fist swipe **right** | `Win+Right` — Snap window right |
| Left open palm + right fist swipe **left** | `Win+Left` — Snap window left |
| Both fists held for **1 second** | `Win+L` — Lock Screen |

---

## Calibration

All parameters live in `config.py` — never scattered across modules.

<details>
<summary><b>Cursor feel</b></summary>

| Symptom | Parameter | Fix |
|---------|-----------|-----|
| Cursor shakes at rest | `ONE_EURO_MINCUTOFF` | Decrease → try `0.3` |
| Cursor lags during fast motion | `ONE_EURO_BETA` | Increase → try `0.05` |
| Cursor drifts near edges | `TRACKPAD_MARGIN` | Increase |

</details>

<details>
<summary><b>Click sensitivity</b></summary>

| Symptom | Parameter | Fix |
|---------|-----------|-----|
| Left click not triggering | `THUMB_INDEX_CLICK_DIST` | Increase → try `0.055` |
| Accidental left clicks | `THUMB_INDEX_CLICK_DIST` | Decrease → try `0.04` |
| Right click not triggering | `THUMB_MIDDLE_CLICK_DIST` | Increase |
| Drag activates too quickly | `DRAG_HOLD_SECONDS` | Increase → try `0.5` |

</details>

<details>
<summary><b>Scroll & zoom</b></summary>

| Symptom | Parameter | Fix |
|---------|-----------|-----|
| Scroll too sensitive | `WRIST_VELOCITY_THRESHOLD` | Increase → try `0.012` |
| Scroll not registering | `WRIST_VELOCITY_THRESHOLD` | Decrease → try `0.005` |
| Zoom fires too easily | `ZOOM_WRIST_DELTA` | Increase → try `0.07` |

</details>

<details>
<summary><b>Performance</b></summary>

| Symptom | Parameter | Fix |
|---------|-----------|-----|
| Low FPS | `CAMERA_WIDTH` / `CAMERA_HEIGHT` | Reduce to `640` / `480` |
| Camera buffer delay | `CAMERA_BUFFER_SIZE` | Keep at `1` |

> MediaPipe dual-hand inference is heavier than single-hand. ~30 FPS at 1280×720 is normal.

</details>

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                            main.py                              │
│  Windows OS tuning → inference loop → cleanup on exit           │
└───────────────┬─────────────────────────────────────────────────┘
                │
    ┌───────────┼───────────────────────────────┐
    │           │                               │
    ▼           ▼                               ▼
camera.py   tracker.py                     actuator.py
Async       MediaPipe                      SendInput (move)
DirectShow  HandLandmarker    ──────────►  pynput (click/key)
daemon      → HandsResult
thread      (left, right)
                │
                ▼
        gestures/orchestrator.py
        Routes HandsResult to sub-processors
                │
    ┌───────────┼───────────────┐
    │           │               │
    ▼           ▼               ▼
right_hand  left_hand       two_hand
Cursor      Win shortcuts   Zoom / Snap
Clicks      Alt+Tab         Lock screen
Scroll      Ctrl modifier
Fist lock
    │
    ▼
filter.py + display.py
1-euro smooth   DPI-aware
cursor          coord map
```

### Why these design choices?

**Thumb as exclusive trigger** — Index stays as pointer; thumb fires everything. No ambiguous combos like "is that a peace sign or a scroll trigger?"

**Wrist velocity for scroll** — Flicking your wrist is anatomically natural and speed-proportional. Faster flick → 1–5 scroll ticks, clamped and cooldown-gated.

**Fist = rest state** — Put your hand down and make a fist. Cursor freezes, no phantom clicks. Open your fingers to resume exactly where you left off.

**`SendInput` over `mouse_event`** — `mouse_event` is a deprecated Vista-era compatibility shim. `SendInput` with `MOUSEEVENTF_VIRTUALDESK` correctly spans all monitors in a virtual desktop.

**DirectShow over MSMF** — `CAP_DSHOW` delivers lower capture latency than the default Media Foundation backend on Windows.

**1-euro filter over Kalman** — Adaptive speed-dependent low-pass filter. Strict reduction in cursor lag vs. Kalman at equivalent jitter suppression (Casiez et al., CHI 2012).

**MediaPipe handedness flip** — MediaPipe labels hands from the camera's point of view. Camera-"Left" = user's right (webcam is a mirror). The tracker flips the label before populating `HandsResult.right`.

---

## Project Structure

```
airmouse/
├── main.py              Entry point — Windows setup + inference loop
├── config.py            Every tunable constant, one file
├── requirements.txt     Dependencies
├── test_startup.py      Smoke tests — run before first use
├── models/              hand_landmarker.task (git-ignored, ~9 MB)
└── core/
    ├── camera.py        Async frame capture via daemon thread
    ├── filter.py        1-euro filter implementation
    ├── display.py       Multi-monitor virtual desktop + DPI mapping
    ├── tracker.py       MediaPipe wrapper → HandsResult dataclass
    ├── actuator.py      Mouse + keyboard injection
    └── gestures/
        ├── orchestrator.py   Coordinates all three processors
        ├── right_hand.py     5-state machine: IDLE/PENDING/DRAG/SCROLL/LOCKED
        ├── left_hand.py      System shortcuts + Ctrl modifier state
        ├── two_hand.py       Zoom / snap / lock-screen
        └── utils.py          dist3d, is_fist, is_peace_sign, is_open_palm, …
```

---

## Troubleshooting

<details>
<summary><b>Camera fails to open</b></summary>

- Open Device Manager and confirm the webcam appears under **Cameras** or **Imaging devices**
- Try setting `CAMERA_INDEX = 1` or `2` in `config.py` if you have multiple cameras
- Ensure privacy shutters are open on laptops with built-in shutters
- Check that no other app (Teams, Zoom, OBS) has exclusive camera access

</details>

<details>
<summary><b>Cursor maps to wrong screen positions</b></summary>

The app sets `PROCESS_PER_MONITOR_DPI_AWARE` at startup. If you use mixed DPI scaling across monitors:
- Set all displays to the same scale (100% or 125%) for initial testing
- Ensure your primary monitor is set correctly in Windows Display Settings

</details>

<details>
<summary><b>Gestures not recognized</b></summary>

- **Lighting**: Diffuse, even lighting works best. Avoid strong backlighting.
- **Distance**: Keep your hand 40–70 cm from the camera.
- **Background**: High-contrast backgrounds help MediaPipe. Avoid skin-tone walls.
- **Thresholds**: Tweak `THUMB_INDEX_CLICK_DIST` or `WRIST_VELOCITY_THRESHOLD` in `config.py`.

</details>

<details>
<summary><b>Low FPS / stuttering</b></summary>

- Dual-hand MediaPipe inference is ~2× heavier than single-hand — 30 FPS at 1280×720 is expected
- Reduce resolution to 640×480 in `config.py` for ~50% FPS improvement
- Close other webcam-consuming applications
- Run as Administrator for `HIGH_PRIORITY_CLASS` and MMCSS "Games" scheduling

</details>

<details>
<summary><b>Permission warnings in logs</b></summary>

`HIGH_PRIORITY_CLASS` and MMCSS thread registration require Administrator privileges. The application functions normally without elevation but may drop frames under CPU load. Run the terminal as Administrator for best performance.

</details>

---

## License

[MIT License](LICENSE) — do whatever you want, just keep the attribution.
