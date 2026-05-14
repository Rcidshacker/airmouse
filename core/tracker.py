# core/tracker.py
"""
MediaPipe Hands wrapper.

Extracts hand landmarks from a BGR frame.
Returns None if no hand is detected; returns a flat list of 21 landmarks otherwise.

Key optimizations applied here:
- model_complexity=0: prioritizes speed, accepts slightly less precise joint angles
- image.flags.writeable = False before process(): prevents MediaPipe from
  copying the numpy array internally, saving 2–5ms per frame (documented in
  MediaPipe source and community benchmarks)
- RGB conversion is mandatory: OpenCV captures BGR, MediaPipe expects RGB
"""

import logging
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np

from config import MP_MODEL_COMPLEXITY, MP_MAX_HANDS, MP_DETECTION_CONFIDENCE, MP_TRACKING_CONFIDENCE

logger = logging.getLogger(__name__)


@dataclass
class Landmark:
    """Normalized [0.0–1.0] landmark coordinate with visibility score."""
    x: float
    y: float
    z: float
    visibility: float = 0.0


# Landmark index constants — MediaPipe Hand Landmark Model
LM_INDEX_TIP = 8       # Cursor control
LM_INDEX_PIP = 6       # Index PIP joint (for scroll detection)
LM_MIDDLE_TIP = 12     # Left-click pinch partner
LM_MIDDLE_PIP = 10
LM_RING_TIP = 16       # Right-click pinch partner
LM_RING_PIP = 14
LM_PINKY_TIP = 20      # Scroll-down gesture
LM_PINKY_PIP = 18
LM_THUMB_TIP = 4
LM_THUMB_MCP = 2


class HandTracker:
    """
    Wraps mediapipe.solutions.hands for single-hand landmark extraction.
    Intended to be used as a context manager.
    """

    def __init__(self) -> None:
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            model_complexity=MP_MODEL_COMPLEXITY,
            max_num_hands=MP_MAX_HANDS,
            min_detection_confidence=MP_DETECTION_CONFIDENCE,
            min_tracking_confidence=MP_TRACKING_CONFIDENCE,
        )
        logger.info(
            "MediaPipe Hands initialized (complexity=%d, max_hands=%d)",
            MP_MODEL_COMPLEXITY, MP_MAX_HANDS,
        )

    def process(self, frame: np.ndarray) -> list[Landmark] | None:
        """
        Process one BGR frame.

        Returns a list of 21 Landmark objects if a hand is detected, else None.
        The frame is not modified.
        """
        try:
            # Convert to RGB first (creates a new array)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Make the RGB array read-only BEFORE passing to MediaPipe.
            # This prevents MediaPipe from copying the array internally,
            # saving 2-5ms per frame (documented in MediaPipe source and benchmarks).
            rgb.flags.writeable = False
            results = self._hands.process(rgb)
        except Exception as e:
            logger.warning("MediaPipe processing error: %s", e)
            return None

        if not results.multi_hand_landmarks:
            return None

        # Take only the first hand
        hand = results.multi_hand_landmarks[0]
        return [
            Landmark(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility)
            for lm in hand.landmark
        ]

    def close(self) -> None:
        self._hands.close()

    def __enter__(self) -> "HandTracker":
        return self

    def __exit__(self, *_) -> None:
        self.close()
