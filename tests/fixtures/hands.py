"""
Synthetic MediaPipe hand landmarks — no camera needed.

Builds an upright hand (fingers pointing up, palm facing the camera) in
normalized image coordinates. Only the geometry the gesture processors read
is modelled: which fingers are extended or curled, and where the thumb tip is.
"""

from __future__ import annotations

from core.tracker import Landmark

# (MCP, PIP, DIP, TIP) landmark indices and the MCP x-offset in hand-scale units
_FINGERS = {
    "index": ((5, 6, 7, 8), -0.30),
    "middle": ((9, 10, 11, 12), -0.10),
    "ring": ((13, 14, 15, 16), 0.10),
    "pinky": ((17, 18, 19, 20), 0.30),
}

# Which fingers are extended:  index, middle, ring, pinky, thumb
_POSES = {
    "open": (True, True, True, True, True),
    "point": (True, False, False, False, True),
    "peace": (True, True, False, False, False),
    "fist": (False, False, False, False, False),
}

_PINCH_TARGET = {"index": 8, "middle": 12}


def make_hand(
    pose: str = "point",
    pinch: str | None = None,
    center: tuple[float, float] = (0.5, 0.6),
    scale: float = 0.15,
) -> list[Landmark]:
    """
    Args:
        pose:   "open", "point", "peace" or "fist"
        pinch:  None, "index" or "middle" — put the thumb tip on that fingertip
        center: wrist position (normalized x, y)
        scale:  wrist → middle-MCP distance in normalized units (hand size in frame)
    """
    cx, cy = center
    s = scale
    extended = dict(zip(("index", "middle", "ring", "pinky", "thumb"), _POSES[pose]))
    pts: list[tuple[float, float]] = [(0.0, 0.0)] * 21

    pts[0] = (cx, cy)  # wrist
    mcp_y = cy - 0.9 * s
    for name, ((mcp, pip, dip, tip), dx) in _FINGERS.items():
        x = cx + dx * s
        pts[mcp] = (x, mcp_y)
        if extended[name]:
            pts[pip] = (x, mcp_y - 0.35 * s)
            pts[dip] = (x, mcp_y - 0.60 * s)
            pts[tip] = (x, mcp_y - 0.80 * s)
        else:  # curled: the tip folds back below the PIP joint
            pts[pip] = (x, mcp_y - 0.25 * s)
            pts[dip] = (x, mcp_y - 0.10 * s)
            pts[tip] = (x, mcp_y + 0.05 * s)

    # Thumb: CMC(1), MCP(2), IP(3), TIP(4) on the index side
    pts[1] = (cx - 0.35 * s, cy - 0.20 * s)
    pts[2] = (cx - 0.50 * s, cy - 0.40 * s)
    if extended["thumb"]:
        pts[3] = (cx - 0.60 * s, cy - 0.55 * s)
        pts[4] = (cx - 0.65 * s, cy - 0.70 * s)
    else:  # tucked across the palm, tip below the thumb MCP
        pts[3] = (cx - 0.35 * s, cy - 0.35 * s)
        pts[4] = (cx - 0.20 * s, cy - 0.30 * s)

    if pinch is not None:
        tx, ty = pts[_PINCH_TARGET[pinch]]
        pts[4] = (tx - 0.05 * s, ty + 0.05 * s)
        pts[3] = ((pts[2][0] + pts[4][0]) / 2, (pts[2][1] + pts[4][1]) / 2)

    return [Landmark(x=x, y=y, z=0.0) for x, y in pts]
