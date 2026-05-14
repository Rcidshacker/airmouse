# AirMouse AI — Bug Fix, Environment Setup & Smoke Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 2 runtime bugs in `core/actuator.py`, update `requirements.txt` for Python 3.13, create a `.venv`, and add a `test_startup.py` smoke test that validates each subsystem.

**Architecture:** Three independent changes — requirements unpin (no code), actuator bug fixes (2 line changes), smoke test (new file). TDD order: write smoke test first (RED), fix bugs to turn it GREEN.

**Tech Stack:** Python 3.13, MediaPipe ≥0.10.30, OpenCV ≥4.10, NumPy ≥2.0, pynput, psutil, screeninfo.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `requirements.txt` | Remove version pins |
| Modify | `core/actuator.py` | Fix `dwExtraInfo=None` + fix `use_last_error` |
| Create | `test_startup.py` | Smoke test — 4 subsystem checks |
| Create | `.venv/` | Python 3.13 virtual environment (git-ignored) |

---

## Task 1: Remove version pins from `requirements.txt`

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Replace the file contents**

```
opencv-python
mediapipe
numpy
screeninfo
pynput
psutil
```

- [ ] **Step 2: Commit**

```bash
git add requirements.txt
git commit -m "chore: unpin deps for Python 3.13 compatibility"
```

---

## Task 2: Create virtual environment and install dependencies

**Files:**
- Create: `.venv/` (git-ignored)

- [ ] **Step 1: Create venv**

Run from the project root (`AirMouse_AI/`):
```bash
python -m venv .venv
```
Expected: `.venv/` directory created. No output on success.

- [ ] **Step 2: Install dependencies**

```bash
.venv\Scripts\pip install -r requirements.txt
```
Expected: pip resolves and installs mediapipe ≥0.10.30, numpy ≥2.0, opencv-python ≥4.10, screeninfo, pynput, psutil. Final line: `Successfully installed ...`

- [ ] **Step 3: Verify key packages installed**

```bash
.venv\Scripts\python -c "import mediapipe, cv2, numpy, screeninfo, pynput, psutil; print('All imports OK')"
```
Expected output: `All imports OK`

If mediapipe fails to import, run:
```bash
.venv\Scripts\pip install --upgrade mediapipe
```

---

## Task 3: Write smoke test `test_startup.py` (RED)

**Files:**
- Create: `test_startup.py`

- [ ] **Step 1: Create the file**

```python
# test_startup.py
"""
Smoke test — validates each subsystem independently.
No inference loop. Run with: python test_startup.py
Exit code 0 = all pass, 1 = any fail.
"""

import sys
import cv2


def test_display() -> None:
    from core.display import build_virtual_desktop, build_trackpad_zone
    desktop = build_virtual_desktop()
    assert desktop.total_width > 0, f"total_width={desktop.total_width}"
    assert desktop.total_height > 0, f"total_height={desktop.total_height}"
    trackpad = build_trackpad_zone()
    assert trackpad.x_max > trackpad.x_min, "trackpad x_max <= x_min"
    assert trackpad.y_max > trackpad.y_min, "trackpad y_max <= y_min"


def test_camera() -> None:
    from config import CAMERA_INDEX
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    assert cap.isOpened(), f"Camera {CAMERA_INDEX} failed to open via DirectShow"
    ret, frame = cap.read()
    cap.release()
    assert ret, "Camera opened but cv2.VideoCapture.read() returned ret=False"
    assert frame is not None, "Camera opened and ret=True but frame is None"


def test_mediapipe() -> None:
    from core.tracker import HandTracker
    tracker = HandTracker()
    tracker.close()


def test_actuator() -> None:
    from core.display import build_virtual_desktop
    from core.actuator import MouseActuator
    desktop = build_virtual_desktop()
    actuator = MouseActuator(desktop.total_width, desktop.total_height)
    actuator.move(0, 0)


TESTS = [
    ("Display geometry", test_display),
    ("Camera open + frame read", test_camera),
    ("MediaPipe HandTracker init", test_mediapipe),
    ("MouseActuator move(0,0)", test_actuator),
]


def main() -> None:
    passed = 0
    failed = 0
    for name, fn in TESTS:
        try:
            fn()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1
    print(f"\n{passed}/{passed + failed} passed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run to observe failures (expected RED state)**

```bash
.venv\Scripts\python test_startup.py
```

Expected: `[FAIL] MouseActuator move(0,0): int expected instead of NoneType` (Bug 1). Bug 2 is silent (wrong error code logging, no crash). Camera and display tests may PASS. MediaPipe may PASS or FAIL depending on version compatibility.

---

## Task 4: Fix Bug 1 — `dwExtraInfo=None` in `core/actuator.py`

**Files:**
- Modify: `core/actuator.py:110`

**Context:** `MOUSEINPUT.dwExtraInfo` is declared `ctypes.c_size_t` (integer type). `None` is not a valid integer — Python ctypes raises `TypeError: int expected instead of NoneType` every time `move()` is called, crashing the app on the first cursor movement.

- [ ] **Step 1: Apply the fix**

In `core/actuator.py`, change line 110:

```python
# Before (BROKEN):
                dwExtraInfo=None,

# After (FIXED):
                dwExtraInfo=0,
```

The full `move()` method's INPUT construction should look like:
```python
        inp = INPUT(
            type=INPUT_MOUSE,
            mi=MOUSEINPUT(
                dx=norm_x,
                dy=norm_y,
                mouseData=0,
                dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
                time=0,
                dwExtraInfo=0,
            ),
        )
```

- [ ] **Step 2: Run actuator smoke test to verify it passes**

```bash
.venv\Scripts\python test_startup.py
```

Expected: `[PASS] MouseActuator move(0,0)` (cursor will jump to 0,0 — top-left of screen).

---

## Task 5: Fix Bug 2 — ineffective `use_last_error` in `core/actuator.py`

**Files:**
- Modify: `core/actuator.py:30` and `core/actuator.py:64`

**Context:** `ctypes.windll.user32` is a cached `LibraryLoader`-managed handle. Setting `use_last_error=True` on it after load does nothing — the attribute is ignored. `ctypes.get_last_error()` always returns 0, so `_send_input`'s warning log always prints `GetLastError=0` even when a real UIPI block or invalid-input error occurred.

Fix: load `user32` explicitly with `ctypes.WinDLL("user32", use_last_error=True)` and use that handle for `SendInput`.

- [ ] **Step 1: Remove the broken line and add the explicit DLL load**

At the top of `core/actuator.py` (near the existing imports, after `logger = ...`), replace:

```python
# Enable accurate last-error retrieval for SendInput diagnostics
ctypes.windll.user32.use_last_error = True
```

with:

```python
_user32 = ctypes.WinDLL("user32", use_last_error=True)
```

- [ ] **Step 2: Update `_send_input` to use `_user32`**

Change the `_send_input` function body from:

```python
def _send_input(inp: INPUT) -> None:
    result = ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    if result == 0:
        err = ctypes.get_last_error()
        logger.warning("SendInput returned 0 (UIPI block or invalid input?). GetLastError=%d", err)
```

to:

```python
def _send_input(inp: INPUT) -> None:
    result = _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    if result == 0:
        err = ctypes.get_last_error()
        logger.warning("SendInput returned 0 (UIPI block or invalid input?). GetLastError=%d", err)
```

- [ ] **Step 3: Run full smoke test**

```bash
.venv\Scripts\python test_startup.py
```

Expected output (all 4 passing):
```
[PASS] Display geometry
[PASS] Camera open + frame read
[PASS] MediaPipe HandTracker init
[PASS] MouseActuator move(0,0)

4/4 passed
```

Exit code: 0

Note: "Camera open + frame read" may [FAIL] if no webcam is connected. That is a hardware issue, not a code bug.

- [ ] **Step 4: Commit all changes**

```bash
git add core/actuator.py test_startup.py
git commit -m "fix: correct dwExtraInfo type and use_last_error DLL load in actuator; add smoke test"
```

---

## Verification

After Task 5 completes successfully, run the full app to confirm end-to-end:

```bash
.venv\Scripts\python main.py
```

Expected log output (first few lines):
```
HH:MM:SS [INFO] airmouse.main: === AI Air Mouse starting ===
HH:MM:SS [INFO] airmouse.main: Windows timer resolution set to 1ms
HH:MM:SS [INFO] core.display: Virtual desktop: NxM across N monitor(s) ...
HH:MM:SS [INFO] core.camera: Camera opened: NxM @ N.0 fps
HH:MM:SS [INFO] core.tracker: MediaPipe Hands initialized (complexity=0, max_hands=1)
HH:MM:SS [INFO] core.actuator: MouseActuator ready (NxM desktop)
HH:MM:SS [INFO] airmouse.main: Running. Press Ctrl+C to exit.
```

Press **Ctrl+C** to exit cleanly. Verify log ends with:
```
HH:MM:SS [INFO] airmouse.main: === AI Air Mouse stopped ===
```
