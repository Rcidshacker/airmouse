# AI Air Mouse

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Windows-10%2B-0078D6.svg" alt="Windows 10+">
  <img src="https://img.shields.io/badge/MediaPipe-0.10-green.svg" alt="MediaPipe">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/Platform-x86__64-lightgrey.svg" alt="x86_64">
</p>

<p align="center">
  <b>Gesture-controlled virtual mouse for Windows.</b><br>
  Move, click, drag, and scroll your cursor using only hand gestures — no touch, no hardware.
</p>

---

AI Air Mouse is a production-grade desktop application that uses your webcam and [MediaPipe Hands](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker) to translate real-time hand tracking into natural mouse control. It runs entirely on-device with zero cloud dependencies, achieving sub-frame latency through a combination of async frame capture, the 1-euro filter for adaptive cursor smoothing, and direct Windows SendInput injection.

## Features

- **Cursor tracking** — Index fingertip mapped to screen coordinates with the [1-euro filter](https://cristal.univ-lille.fr/~casiez/1euro/) for jitter-free, lag-free movement
- **Left click** — Quick pinch of index + middle fingertips
- **Right click** — Quick pinch of index + ring fingertips
- **Drag & drop** — Hold index + middle pinch beyond the drag threshold (0.25s default)
- **Scroll up/down** — Three-finger open hand (scroll up) or pinky extension (scroll down)
- **Multi-monitor support** — DPI-aware virtual desktop spanning across all connected displays
- **Async capture** — Dedicated daemon thread for non-blocking frame reads at native webcam FPS
- **Windows real-time tuning** — 1ms timer resolution, `HIGH_PRIORITY_CLASS`, MMCSS "Games" thread registration, pointer acceleration suppression

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.11 | 3.12 |
| Windows | 10 | 11 |
| Webcam | Any DirectShow-compatible USB or built-in camera | 60 FPS capable |
| RAM | 2 GB | 4 GB+ |

Administrator access is recommended (not required) for process priority elevation and MMCSS registration.

## Quick Start

```bash
git clone https://github.com/Rcidshacker/airmouse.git
cd airmouse
pip install -r requirements.txt
python main.py
```

Press **Ctrl+C** to exit. All system settings are automatically restored on shutdown.

## Gesture Reference

| Gesture | Action | Trigger |
|---------|--------|---------|
| Point index finger | Move cursor | Tracks fingertip with 1-euro filter smoothing |
| Pinch index + middle (tap) | Left click | Euclidean distance between landmarks 8 and 12 drops below threshold |
| Pinch index + ring (tap) | Right click | Euclidean distance between landmarks 8 and 16 drops below threshold |
| Pinch index + middle (hold 0.25s+) | Drag & drop | Sustained left pinch transitions to drag mode; release to drop |
| Three fingers open (index, middle, ring extended; thumb + pinky curled) | Scroll up | Recognized via fingertip-vs-PIP joint comparison |
| Pinky extended (index, middle, ring curled) | Scroll down | Recognized via fingertip-vs-PIP joint comparison |

All discrete gestures (clicks, scrolls) enforce a cooldown of 0.4 seconds to prevent accidental double-triggers.

## Calibration

All tunable parameters are centralized in `config.py` — never scatter constants across modules.

| Symptom | Parameter to adjust | Direction |
|---------|-------------------|-----------|
| Cursor jittery at rest | `ONE_EURO_MINCUTOFF` | Decrease (try 0.5) |
| Cursor lags during fast motion | `ONE_EURO_BETA` | Increase (try 0.05) |
| Gestures not triggering | `CLICK_DISTANCE_THRESHOLD` | Increase (try 0.06) |
| False positive gestures | `CLICK_DISTANCE_THRESHOLD` | Decrease (try 0.035) |
| Tracking area too small | `TRACKPAD_MARGIN` | Decrease |
| Drag too sensitive | `DRAG_HOLD_SECONDS` | Increase (try 0.35) |
| Low FPS | `CAMERA_WIDTH` / `CAMERA_HEIGHT` | Reduce to 640x480 |

## Architecture

```
main.py                           Entry point + Windows OS tuning + inference loop
  |
  +-- core/camera.py              Async frame capture (daemon thread, DirectShow)
  +-- core/tracker.py             MediaPipe Hands wrapper (21 landmarks)
  +-- core/gestures.py            Gesture state machine (5 gestures + cursor)
  |     |
  |     +-- core/filter.py        1-euro filter (Casiez et al., CHI 2012)
  |     +-- core/display.py       Multi-monitor DPI-aware coordinate mapping
  |     +-- core/actuator.py      Windows SendInput + pynput mouse injection
  |
  +-- config.py                   Single source of truth for all tunables
```

### Key Design Decisions

- **SendInput over `mouse_event`**: `mouse_event` is deprecated since Vista; SendInput is the documented low-overhead replacement.
- **SendInput for movement, pynput for clicks**: pynput wraps SendInput internally, so direct ctypes for movement eliminates one layer. pynput is retained for click/drag because its press/release abstraction is cleaner than manual button flag management.
- **DirectShow over MSMF**: DirectShow backend (`CAP_DSHOW`) provides lower capture latency than the default Media Foundation on Windows.
- **1-euro filter over Kalman**: The 1-euro filter is a speed-dependent adaptive low-pass filter that strictly outperforms Kalman for 2D cursor trajectories (Casiez et al., CHI 2012).
- **Buffer size 1**: Forces the capture thread to always grab the freshest frame, eliminating queued-frame staleness.

## Troubleshooting

### Camera fails to open
Verify the webcam is connected in Device Manager. Try changing `CAMERA_INDEX` in `config.py` to `1` or `2` for multi-camera setups. Ensure privacy shutters are open on laptops.

### Cursor maps to wrong positions
The application sets `PROCESS_PER_MONITOR_DPI_AWARE` at startup. If you use custom DPI scaling, try setting all monitors to the same scale (100% or 125%) for initial testing.

### Low FPS
Close other webcam-consuming apps (Zoom, Teams, OBS). Check the log for actual camera FPS — some webcams cannot sustain 60 FPS at 1280x720. Reduce resolution to 640x480 in `config.py` if needed.

### Permission warnings
`HIGH_PRIORITY_CLASS` and MMCSS registration require Administrator privileges. The application still functions without elevation, but may experience occasional frame drops under system load.

## Project Structure

```
airmouse/
├── main.py            # Entry point, Windows OS setup, main inference loop
├── config.py          # All tunable parameters (single source of truth)
├── requirements.txt   # Pinned dependencies
├── .gitignore         # Git ignore rules
├── README.md          # This file
└── core/
    ├── __init__.py
    ├── camera.py      # Asynchronous frame capture via daemon thread
    ├── filter.py      # 1-euro filter (Casiez et al. 2012) for cursor smoothing
    ├── display.py     # Multi-monitor virtual desktop mapping, DPI awareness
    ├── tracker.py     # MediaPipe Hands wrapper for landmark extraction
    ├── gestures.py    # Gesture recognition state machine
    └── actuator.py    # Windows SendInput mouse actuation
```

## License

This project is licensed under the [MIT License](LICENSE).
