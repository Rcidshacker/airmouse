# core/gestures/utils.py
"""Shared landmark geometry helpers used by all gesture processors."""

import numpy as np
from core.tracker import Landmark


def dist3d(a: Landmark, b: Landmark) -> float:
    """3D Euclidean distance in normalized MediaPipe coordinate space."""
    return float(np.linalg.norm([a.x - b.x, a.y - b.y, a.z - b.z]))


def is_extended(tip: Landmark, pip: Landmark) -> bool:
    """Finger extended = tip is above (lower y) its PIP joint. MediaPipe y=0 is top."""
    return tip.y < pip.y


def is_curled(tip: Landmark, pip: Landmark) -> bool:
    return tip.y > pip.y


def is_fist(lm: list[Landmark]) -> bool:
    """All 5 fingers curled."""
    return (
        is_curled(lm[8],  lm[6])   # index
        and is_curled(lm[12], lm[10])  # middle
        and is_curled(lm[16], lm[14])  # ring
        and is_curled(lm[20], lm[18])  # pinky
        and is_curled(lm[4],  lm[2])   # thumb (tip vs MCP)
    )


def is_peace_sign(lm: list[Landmark]) -> bool:
    """Index + middle extended, thumb + ring + pinky curled."""
    return (
        is_extended(lm[8],  lm[6])    # index extended
        and is_extended(lm[12], lm[10])   # middle extended
        and is_curled(lm[16],  lm[14])   # ring curled
        and is_curled(lm[20],  lm[18])   # pinky curled
        and is_curled(lm[4],   lm[2])    # thumb curled (prevents conflict with open hand)
    )


def is_open_palm(lm: list[Landmark]) -> bool:
    """All 5 fingers extended."""
    return (
        is_extended(lm[8],  lm[6])
        and is_extended(lm[12], lm[10])
        and is_extended(lm[16], lm[14])
        and is_extended(lm[20], lm[18])
        and is_extended(lm[4],  lm[2])
    )


def is_v_sign(lm: list[Landmark]) -> bool:
    """Index + middle extended, ring + pinky curled (thumb free)."""
    return (
        is_extended(lm[8],  lm[6])
        and is_extended(lm[12], lm[10])
        and is_curled(lm[16],  lm[14])
        and is_curled(lm[20],  lm[18])
    )


def is_four_fingers(lm: list[Landmark]) -> bool:
    """Index + middle + ring + pinky extended, thumb curled."""
    return (
        is_extended(lm[8],  lm[6])
        and is_extended(lm[12], lm[10])
        and is_extended(lm[16], lm[14])
        and is_extended(lm[20], lm[18])
        and is_curled(lm[4],   lm[2])
    )
