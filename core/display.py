# core/display.py
"""
Multi-monitor virtual desktop mapping.

Responsibilities:
- Set Windows DPI awareness so coordinate queries return physical pixels
- Query all connected displays via screeninfo
- Build a unified virtual bounding box (sum of all screen widths)
- Expose numpy.interp-based coordinate translation from webcam trackpad to desktop
"""

import ctypes
import logging
import sys
from dataclasses import dataclass

import numpy as np
from screeninfo import get_monitors

from config import TRACKPAD_MARGIN, CAMERA_WIDTH, CAMERA_HEIGHT

logger = logging.getLogger(__name__)


def _set_dpi_awareness() -> None:
    """
    SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE = 2).
    Must be called before any screen coordinate queries.
    Without this, Windows returns logical (scaled) pixels, not physical pixels,
    breaking coordinate mapping on HiDPI displays.
    Falls back to the older SetProcessDPIAware() on Windows 7.
    No-op on non-Windows platforms.
    """
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        logger.debug("DPI awareness: PROCESS_PER_MONITOR_DPI_AWARE")
    except AttributeError:
        ctypes.windll.user32.SetProcessDPIAware()
        logger.debug("DPI awareness: legacy SetProcessDPIAware")
    except OSError as e:
        logger.warning("Could not set DPI awareness: %s", e)


@dataclass(frozen=True)
class VirtualDesktop:
    """
    Immutable snapshot of the virtual desktop geometry.
    All values are in physical pixels.
    """
    total_width: int     # Sum of all monitor widths
    total_height: int    # Height of the tallest monitor
    monitor_count: int


def build_virtual_desktop() -> VirtualDesktop:
    """
    Query all connected monitors and construct the virtual desktop bounding box.
    Uses monitor offsets to correctly handle stacked, L-shaped, and gapped layouts.
    Must be called after _set_dpi_awareness().
    """
    monitors = get_monitors()
    if not monitors:
        raise RuntimeError("screeninfo returned no monitors — cannot build virtual desktop")

    min_x = min(m.x for m in monitors)
    max_x = max(m.x + m.width for m in monitors)
    min_y = min(m.y for m in monitors)
    max_y = max(m.y + m.height for m in monitors)

    total_w = max_x - min_x
    total_h = max_y - min_y

    logger.info(
        "Virtual desktop: %dx%d across %d monitor(s) (origin at %d,%d)",
        total_w, total_h, len(monitors), min_x, min_y
    )
    for i, m in enumerate(monitors):
        logger.debug("  Monitor %d: %s (%dx%d at %d,%d)", i, m.name, m.width, m.height, m.x, m.y)

    return VirtualDesktop(
        total_width=total_w,
        total_height=total_h,
        monitor_count=len(monitors),
    )


@dataclass(frozen=True)
class TrackpadZone:
    """
    The active region of the webcam frame used for tracking.
    Shrunk inward by TRACKPAD_MARGIN on all sides so the user
    doesn't need to stretch their hand to the camera's extreme edges.
    """
    x_min: int
    x_max: int
    y_min: int
    y_max: int


def build_trackpad_zone() -> TrackpadZone:
    return TrackpadZone(
        x_min=TRACKPAD_MARGIN,
        x_max=CAMERA_WIDTH - TRACKPAD_MARGIN,
        y_min=TRACKPAD_MARGIN,
        y_max=CAMERA_HEIGHT - TRACKPAD_MARGIN,
    )


def map_to_desktop(
    norm_x: float,
    norm_y: float,
    trackpad: TrackpadZone,
    desktop: VirtualDesktop,
) -> tuple[int, int]:
    """
    Translate normalized MediaPipe coordinates [0.0–1.0] to physical desktop pixels.

    MediaPipe returns normalized coords; we first scale to webcam pixel space,
    then clamp to the trackpad zone, then interpolate to desktop space.

    Args:
        norm_x: Normalized x from MediaPipe (0.0 = left edge of frame)
        norm_y: Normalized y from MediaPipe (0.0 = top edge of frame)
        trackpad: Active webcam zone
        desktop: Virtual desktop geometry

    Returns:
        (screen_x, screen_y) in physical desktop pixels
    """
    # Mirror x-axis: webcam sees user's right as image-left, so invert
    # for natural 1:1 hand-to-cursor mapping (move hand right -> cursor right)
    px = (1.0 - norm_x) * CAMERA_WIDTH
    py = norm_y * CAMERA_HEIGHT

    # Clamp to trackpad zone
    px = max(trackpad.x_min, min(trackpad.x_max, px))
    py = max(trackpad.y_min, min(trackpad.y_max, py))

    # Interpolate to desktop space
    screen_x = int(np.interp(px, [trackpad.x_min, trackpad.x_max], [0, desktop.total_width - 1]))
    screen_y = int(np.interp(py, [trackpad.y_min, trackpad.y_max], [0, desktop.total_height - 1]))

    return screen_x, screen_y


# Run DPI awareness setup at import time — must happen before any screen query
_set_dpi_awareness()
