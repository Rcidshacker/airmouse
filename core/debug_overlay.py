# core/debug_overlay.py
"""
Debug overlay — draws hand landmarks, L/R labels, gesture state, and pinch
distances onto the camera frame. Only imported when DEBUG_GESTURES = True.
"""

import cv2
import numpy as np

from core.tracker import HandsResult, Landmark

# Standard MediaPipe hand skeleton connections
_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),          # index
    (5, 9), (9, 10), (10, 11), (11, 12),     # middle
    (9, 13), (13, 14), (14, 15), (15, 16),   # ring
    (13, 17), (17, 18), (18, 19), (19, 20),  # pinky
    (0, 17), (5, 9), (9, 13), (13, 17),      # palm
]

_GREEN  = (0, 220, 80)
_ORANGE = (0, 160, 255)
_WHITE  = (255, 255, 255)
_YELLOW = (0, 215, 255)
_FONT   = cv2.FONT_HERSHEY_SIMPLEX


def _lm_px(lm: Landmark, w: int, h: int) -> tuple[int, int]:
    return int(lm.x * w), int(lm.y * h)


def _draw_hand(img: np.ndarray, lms: list[Landmark], color: tuple, label: str) -> None:
    h, w = img.shape[:2]
    for a, b in _CONNECTIONS:
        cv2.line(img, _lm_px(lms[a], w, h), _lm_px(lms[b], w, h), color, 1, cv2.LINE_AA)
    for lm in lms:
        cv2.circle(img, _lm_px(lm, w, h), 4, color, -1, cv2.LINE_AA)
    # Label at wrist
    wx, wy = _lm_px(lms[0], w, h)
    cv2.putText(img, label, (wx + 12, wy - 8), _FONT, 0.8, color, 2, cv2.LINE_AA)


def draw_debug_frame(
    frame: np.ndarray,
    hands: HandsResult,
    right_state: str,
) -> np.ndarray:
    """
    Returns a copy of frame with:
      - Green skeleton + 'R' label for right hand
      - Orange skeleton + 'L' label for left hand
      - HUD: state, thumb-index dist, thumb-middle dist, hand-presence indicators
    """
    import math

    out = frame.copy()
    h, w = out.shape[:2]

    if hands.right is not None:
        _draw_hand(out, hands.right, _GREEN, "R (RIGHT)")
        # Thumb-index distance
        t, i = hands.right[4], hands.right[8]
        d_ti = math.sqrt((t.x - i.x)**2 + (t.y - i.y)**2 + (t.z - i.z)**2)
        # Thumb-middle distance
        m = hands.right[12]
        d_tm = math.sqrt((t.x - m.x)**2 + (t.y - m.y)**2 + (t.z - m.z)**2)
        # Draw pinch lines
        cv2.line(out, _lm_px(t, w, h), _lm_px(i, w, h), _YELLOW, 2, cv2.LINE_AA)
        cv2.line(out, _lm_px(t, w, h), _lm_px(m, w, h), (180, 100, 255), 2, cv2.LINE_AA)
        ti_text = f"T-I: {d_ti:.3f}"
        tm_text = f"T-M: {d_tm:.3f}"
    else:
        ti_text = "T-I: --"
        tm_text = "T-M: --"

    if hands.left is not None:
        _draw_hand(out, hands.left, _ORANGE, "L (LEFT)")

    # HUD — top-left panel
    hud_lines = [
        f"State : {right_state}",
        ti_text + "  (click<0.060)",
        tm_text + "  (rclick<0.065)",
        f"R hand: {'DETECTED' if hands.right is not None else 'absent'}",
        f"L hand: {'DETECTED' if hands.left  is not None else 'absent'}",
        "Q = quit debug window",
    ]
    pad = 8
    line_h = 22
    box_h = len(hud_lines) * line_h + pad * 2
    box_w = 310
    cv2.rectangle(out, (0, 0), (box_w, box_h), (30, 30, 30), -1)
    for idx, line in enumerate(hud_lines):
        color = _GREEN if "DETECTED" in line else _WHITE
        cv2.putText(out, line, (pad, pad + line_h * (idx + 1) - 4),
                    _FONT, 0.52, color, 1, cv2.LINE_AA)

    return out
