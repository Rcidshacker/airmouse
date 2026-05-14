# core/actuator.py
"""
Windows mouse actuation via SendInput.

Why SendInput over mouse_event:
- mouse_event is deprecated since Windows Vista; routes through a compatibility shim
- SendInput is the documented, low-overhead replacement
- MOUSEEVENTF_VIRTUALDESK + MOUSEEVENTF_ABSOLUTE correctly spans all monitors

Why SendInput over pynput for movement:
- pynput wraps SendInput anyway; calling ctypes directly removes one layer
- pynput is used here only for click/drag state because its press/release
  abstraction is cleaner than manually managing button flags in INPUT structs

Coordinate system for MOUSEEVENTF_ABSOLUTE:
- The virtual desktop is mapped to a normalized space of [0, 65535] x [0, 65535]
- Physical pixel (x, y) -> norm = (x * 65535 / total_w, y * 65535 / total_h)
- MOUSEEVENTF_VIRTUALDESK flag makes (65535, 65535) = bottom-right of ALL monitors
  Without this flag, (65535, 65535) = bottom-right of the PRIMARY monitor only
"""

import ctypes
import logging

from pynput.mouse import Button, Controller as MouseController

logger = logging.getLogger(__name__)

_user32 = ctypes.WinDLL("user32", use_last_error=True)

# ── SendInput ctypes structures ───────────────────────────────────────────────

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          ctypes.c_long),
        ("dy",          ctypes.c_long),
        ("mouseData",   ctypes.c_ulong),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("_u",)
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("_u",   _INPUT_UNION),
    ]


INPUT_MOUSE              = 0
MOUSEEVENTF_MOVE         = 0x0001
MOUSEEVENTF_ABSOLUTE     = 0x8000
MOUSEEVENTF_VIRTUALDESK  = 0x4000   # Interpret absolute coords as virtual desktop coords


def _send_input(inp: INPUT) -> None:
    result = _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    if result == 0:
        err = ctypes.get_last_error()
        logger.warning("SendInput returned 0 (UIPI block or invalid input?). GetLastError=%d", err)


# ── Public Actuator ───────────────────────────────────────────────────────────

class MouseActuator:
    """
    Handles all mouse movement and click state.

    Args:
        total_width:  Physical pixel width of the full virtual desktop
        total_height: Physical pixel height of the full virtual desktop
    """

    def __init__(self, total_width: int, total_height: int) -> None:
        self._total_w = total_width
        self._total_h = total_height
        self._pynput = MouseController()
        self._dragging = False
        logger.info("MouseActuator ready (%dx%d desktop)", total_width, total_height)

    def move(self, x: int, y: int) -> None:
        """
        Move cursor to absolute desktop coordinates (physical pixels).
        Maps to SendInput's [0, 65535] normalized space.
        """
        norm_x = int(x * 65535 / max(self._total_w - 1, 1))
        norm_y = int(y * 65535 / max(self._total_h - 1, 1))

        # Clamp to valid range
        norm_x = max(0, min(65535, norm_x))
        norm_y = max(0, min(65535, norm_y))

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
        _send_input(inp)

    def left_click(self) -> None:
        self._pynput.click(Button.left)

    def right_click(self) -> None:
        self._pynput.click(Button.right)

    def drag_start(self) -> None:
        if not self._dragging:
            self._pynput.press(Button.left)
            self._dragging = True
            logger.debug("Drag started")

    def drag_end(self) -> None:
        if self._dragging:
            self._pynput.release(Button.left)
            self._dragging = False
            logger.debug("Drag ended")

    def scroll(self, ticks: int) -> None:
        """
        Scroll vertically. Positive ticks = scroll up, negative = scroll down.
        """
        self._pynput.scroll(0, ticks)

    @property
    def is_dragging(self) -> bool:
        return self._dragging
