# core/gestures/orchestrator.py
"""
GestureOrchestrator — routes HandsResult to per-hand processors.

Exposes process(hands: HandsResult) as a drop-in replacement for
the old GestureProcessor.process(landmarks: list[Landmark]).
"""

import logging

from config import LEFT_HAND_ENABLED, TWO_HAND_GESTURES_ENABLED
from core.tracker import HandsResult
from core.display import VirtualDesktop, TrackpadZone
from core.actuator import MouseActuator
from core.gestures.right_hand import RightHandProcessor
from core.gestures.left_hand import LeftHandProcessor
from core.gestures.two_hand import TwoHandProcessor

logger = logging.getLogger(__name__)


class GestureOrchestrator:
    """
    Coordinates right, left, and two-hand processors.

    Args:
        actuator: MouseActuator instance
        desktop:  VirtualDesktop for coordinate mapping
        trackpad: TrackpadZone for coordinate mapping
        left_hand_enabled: run the left-hand shortcut layer (default: config)
        two_hand_enabled:  run the two-hand gesture layer (default: config)
    """

    def __init__(
        self,
        actuator: MouseActuator,
        desktop: VirtualDesktop,
        trackpad: TrackpadZone,
        left_hand_enabled: bool = LEFT_HAND_ENABLED,
        two_hand_enabled: bool = TWO_HAND_GESTURES_ENABLED,
    ) -> None:
        self._right = RightHandProcessor(actuator, desktop, trackpad)
        self._left = LeftHandProcessor(actuator) if left_hand_enabled else None
        self._two = TwoHandProcessor(actuator) if two_hand_enabled else None
        logger.info(
            "GestureOrchestrator ready (left hand: %s, two-hand gestures: %s)",
            "on" if left_hand_enabled else "off",
            "on" if two_hand_enabled else "off",
        )

    def process(self, hands: HandsResult) -> None:
        """Process one frame. Call once per frame regardless of hand visibility."""
        self._right.process(hands.right)

        if self._left is not None:
            # None releases any held modifier when the left hand leaves the frame
            self._left.process(hands.left)

        if self._two is not None and hands.left is not None and hands.right is not None:
            self._two.process(hands.left, hands.right)

    @property
    def right_state(self) -> str:
        return self._right._state.name
