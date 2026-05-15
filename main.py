# main.py
"""
AI Air Mouse — Entry point.

Startup sequence (ORDER MATTERS):
  1. Configure logging
  2. Set Windows timer resolution to 1ms
  3. Elevate process to HIGH_PRIORITY_CLASS
  4. Register main thread with MMCSS ("Games" profile)
  5. Build virtual desktop + trackpad zone (DPI awareness already set at display.py import)
  6. Disable Windows pointer acceleration (restore on exit)
  7. Start async camera
  8. Start MediaPipe hand tracker
  9. Instantiate gesture processor + actuator
  10. Run inference loop
  11. On exit: restore timer resolution, restore pointer precision, release all resources

Exit handling:
  - Ctrl+C (KeyboardInterrupt) -> clean shutdown
  - Any unhandled exception -> log traceback, then clean shutdown
  - atexit handler as final safety net to ensure pointer precision is restored
"""

import atexit
import ctypes
import logging
import os
import time
import traceback

import psutil

from config import PROCESS_PRIORITY, TIMER_RESOLUTION_MS
from core.camera import AsyncCamera
from core.tracker import HandTracker
from core.gestures import GestureProcessor
from core.actuator import MouseActuator
from core.display import build_virtual_desktop, build_trackpad_zone

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("airmouse.main")


# ── Windows OS Setup ──────────────────────────────────────────────────────────

def _apply_windows_performance() -> dict:
    """
    Apply all Windows OS performance settings.
    Returns a dict of original values so they can be restored on exit.
    """
    original = {}

    # 1. Timer resolution: set to 1ms floor (default is 15.6ms)
    try:
        winmm = ctypes.windll.winmm
        winmm.timeBeginPeriod(TIMER_RESOLUTION_MS)
        original["timer_period"] = TIMER_RESOLUTION_MS
        logger.info("Windows timer resolution set to %dms", TIMER_RESOLUTION_MS)
    except Exception as e:
        logger.warning("Failed to set timer resolution: %s", e)

    # 2. Process priority: HIGH_PRIORITY_CLASS
    try:
        proc = psutil.Process(os.getpid())
        proc.nice(PROCESS_PRIORITY)
        logger.info("Process priority set to HIGH_PRIORITY_CLASS (0x%X)", PROCESS_PRIORITY)
    except psutil.AccessDenied:
        logger.warning("Could not elevate process priority — run as administrator for best performance")

    # 3. MMCSS: register main thread as "Games" workload class
    # This tells the Windows scheduler to give us CPU time more aggressively
    # and deprioritize background tasks (Defender, Windows Update, etc.) relative to us.
    try:
        avrt = ctypes.windll.avrt
        task_index = ctypes.c_ulong(0)
        avrt.AvSetMmThreadCharacteristicsW.restype = ctypes.c_void_p
        handle = avrt.AvSetMmThreadCharacteristicsW("Games", ctypes.byref(task_index))
        if handle:
            original["mmcss_handle"] = handle
            logger.info("MMCSS thread registered as 'Games' (handle=%d)", handle)
        else:
            logger.warning("MMCSS registration returned NULL handle")
    except Exception as e:
        logger.warning("MMCSS registration failed: %s", e)

    # 4. Disable "Enhance Pointer Precision" (Windows mouse acceleration)
    # This ballistic curve applied by Windows corrupts the 1€ Filter output.
    # SPI_GETMOUSE = 3, SPI_SETMOUSE = 4
    # The parameter is [threshold1, threshold2, acceleration]
    # acceleration=0 disables enhance pointer precision
    original_mouse_params = (ctypes.c_int * 3)(0, 0, 0)
    get_result = ctypes.windll.user32.SystemParametersInfoW(3, 0, original_mouse_params, 0)
    if not get_result:
        logger.warning("SystemParametersInfoW(SPI_GETMOUSE) failed — cannot save/restore mouse settings")
    else:
        original["mouse_params"] = list(original_mouse_params)
        no_accel = (ctypes.c_int * 3)(0, 0, 0)
        set_result = ctypes.windll.user32.SystemParametersInfoW(4, 0, no_accel, 2)
        if not set_result:
            logger.warning("SystemParametersInfoW(SPI_SETMOUSE) failed — pointer acceleration may not be disabled")
        else:
            logger.info("Windows pointer acceleration disabled")

    return original


def _restore_windows_settings(original: dict) -> None:
    """Restore all Windows settings mutated during startup."""

    # Restore timer resolution
    if "timer_period" in original:
        ctypes.windll.winmm.timeEndPeriod(original["timer_period"])
        logger.info("Windows timer resolution restored")

    # Unregister MMCSS
    if "mmcss_handle" in original:
        try:
            ctypes.windll.avrt.AvRevertMmThreadCharacteristics(original["mmcss_handle"])
            logger.info("MMCSS thread unregistered")
        except Exception as e:
            logger.warning("MMCSS revert failed: %s", e)

    # Restore pointer precision
    if "mouse_params" in original:
        restored = (ctypes.c_int * 3)(*original["mouse_params"])
        ctypes.windll.user32.SystemParametersInfoW(4, 0, restored, 2)
        logger.info("Windows pointer acceleration restored")


# ── Main Loop ─────────────────────────────────────────────────────────────────

def run() -> None:
    original_settings: dict = {}

    def _emergency_restore():
        """atexit safety net — runs even on unhandled exceptions."""
        if original_settings:
            _restore_windows_settings(original_settings)

    atexit.register(_emergency_restore)

    logger.info("=== AI Air Mouse starting ===")

    # Apply OS settings before anything else
    original_settings.update(_apply_windows_performance())

    # Build display geometry
    desktop = build_virtual_desktop()
    trackpad = build_trackpad_zone()

    # Instantiate subsystems
    actuator = MouseActuator(desktop.total_width, desktop.total_height)

    frame_count = 0
    fps_clock = time.perf_counter()
    none_count = 0

    with AsyncCamera() as camera, HandTracker() as tracker:
        processor = GestureProcessor(actuator, desktop, trackpad)

        logger.info("Running. Press Ctrl+C to exit.")

        try:
            while True:
                frame = camera.read()

                if frame is None:
                    # First frames haven't arrived yet — yield briefly
                    none_count += 1
                    if none_count > 5000:  # ~5 seconds of no frames
                        logger.error("Camera produced no frames for ~5 seconds — camera may be disconnected")
                        break
                    time.sleep(0.001)
                    continue

                none_count = 0

                landmarks = tracker.process(frame)

                if landmarks is not None:
                    processor.process(landmarks)

                # FPS telemetry — log once per 5 seconds
                frame_count += 1
                now = time.perf_counter()
                if now - fps_clock >= 5.0:
                    fps = frame_count / (now - fps_clock)
                    logger.info("FPS: %.1f", fps)
                    frame_count = 0
                    fps_clock = now

        except KeyboardInterrupt:
            logger.info("Ctrl+C received — shutting down cleanly")
        except Exception:
            logger.error("Unhandled exception:\n%s", traceback.format_exc())
        finally:
            # Ensure drag is never left pressed on exit
            if actuator.is_dragging:
                actuator.drag_end()
            _restore_windows_settings(original_settings)
            original_settings.clear()  # prevent atexit double-restore
            logger.info("=== AI Air Mouse stopped ===")


if __name__ == "__main__":
    run()
