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
