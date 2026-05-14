# AirMouse AI — Bug Fix, Environment Setup & Smoke Test Design

**Date:** 2026-05-14  
**Scope:** Fix 2 code bugs in `core/actuator.py`, update `requirements.txt` for Python 3.13, create venv, add smoke test.

---

## 1. Bug Fixes — `core/actuator.py`

### Bug 1: `dwExtraInfo=None` (line 110)

`MOUSEINPUT.dwExtraInfo` is declared as `ctypes.c_size_t` (integer). Passing `None` raises `TypeError` on every `move()` call — the app crashes immediately on first cursor movement.

**Fix:** Change `dwExtraInfo=None` → `dwExtraInfo=0`.

### Bug 2: Ineffective `use_last_error` (line 30)

`ctypes.windll.user32.use_last_error = True` sets an attribute on an already-cached DLL handle. ctypes ignores it; `ctypes.get_last_error()` always returns 0. SendInput errors are silently swallowed with a misleading `GetLastError=0` log.

**Fix:** Load user32 explicitly at module level:
```python
_user32 = ctypes.WinDLL("user32", use_last_error=True)
```
Replace all `ctypes.windll.user32.SendInput(...)` calls with `_user32.SendInput(...)`.

---

## 2. Environment Setup

### Python Version
Python 3.13 (system-installed). No additional Python version required.

### `requirements.txt`
Remove all version pins. Let pip resolve latest Python 3.13 compatible wheels:
```
opencv-python
mediapipe
numpy
screeninfo
pynput
psutil
```
Expected resolved versions: mediapipe ≥0.10.30, numpy ≥2.0, opencv-python ≥4.10.

### Virtual Environment
- Location: `AirMouse_AI/.venv`
- Create: `python -m venv .venv`
- Activate: `.venv\Scripts\activate`
- Install: `pip install -r requirements.txt`

---

## 3. Smoke Test — `test_startup.py`

New file at project root. Validates each subsystem in isolation — no inference loop, no gesture processing.

### Test Cases

| # | Name | What it tests | Pass condition |
|---|------|---------------|----------------|
| 1 | Display geometry | `build_virtual_desktop()` + `build_trackpad_zone()` | `total_width > 0`, no exception |
| 2 | Camera open | `cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)` | `isOpened()` True, one frame reads OK |
| 3 | MediaPipe init | `HandTracker()` instantiation + `close()` | No exception |
| 4 | Actuator move | `MouseActuator(w, h).move(0, 0)` | No exception, SendInput returns 1 |

### Exit Behavior
- Print `[PASS]` / `[FAIL] reason` per test
- Exit code 0 if all pass, 1 if any fail

### Constraints
- No imports from `main.py` (avoids triggering Windows OS tuning)
- Camera is released immediately after reading one frame
- Does not leave mouse pressed or dragging

---

## Out of Scope

- Debug preview window (headless preferred)
- New gestures or gesture tuning
- Type annotation additions beyond what already exists
- CI/CD setup
