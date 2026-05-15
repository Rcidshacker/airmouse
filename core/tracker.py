# core/tracker.py
"""
MediaPipe HandLandmarker wrapper (Tasks API — mediapipe ≥0.10.14).

Extracts hand landmarks from a BGR frame.
Returns None if no hand detected; returns list of 21 Landmark objects otherwise.

Key optimizations:
- RunningMode.IMAGE: simplest mode, stateless per-frame inference
- RGB conversion + mp.Image wrapper: required by Tasks API
- No internal array copy: mp.Image takes ownership of the numpy buffer
"""

import logging
from dataclasses import dataclass

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
import numpy as np

from config import MP_DETECTION_CONFIDENCE, MP_TRACKING_CONFIDENCE, MP_MODEL_PATH

logger = logging.getLogger(__name__)


@dataclass
class Landmark:
    """Normalized [0.0–1.0] landmark coordinate."""
    x: float
    y: float
    z: float
    visibility: float = 0.0


@dataclass
class HandsResult:
    """Holds landmarks for both hands. None = that hand not detected this frame."""
    left: list[Landmark] | None = None   # user's left hand (21 landmarks)
    right: list[Landmark] | None = None  # user's right hand (21 landmarks)


# Landmark index constants — MediaPipe Hand Landmark Model
LM_INDEX_TIP = 8
LM_INDEX_PIP = 6
LM_MIDDLE_TIP = 12
LM_MIDDLE_PIP = 10
LM_RING_TIP = 16
LM_RING_PIP = 14
LM_PINKY_TIP = 20
LM_PINKY_PIP = 18
LM_THUMB_TIP = 4
LM_THUMB_MCP = 2


class HandTracker:
    """
    Wraps MediaPipe HandLandmarker (Tasks API) for single-hand landmark extraction.
    Intended to be used as a context manager.
    """

    def __init__(self) -> None:
        base_options = python.BaseOptions(model_asset_path=MP_MODEL_PATH)
        options = HandLandmarkerOptions(
            base_options=base_options,
            running_mode=RunningMode.IMAGE,
            num_hands=2,
            min_hand_detection_confidence=MP_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=MP_TRACKING_CONFIDENCE,
            min_tracking_confidence=MP_TRACKING_CONFIDENCE,
        )
        self._detector = HandLandmarker.create_from_options(options)
        logger.info("MediaPipe HandLandmarker initialized (max_hands=2)")

    def process(self, frame: np.ndarray) -> HandsResult:
        """
        Process one BGR frame. Always returns HandsResult (never None).
        Each field is None if that hand was not detected.

        MediaPipe 'Left' from camera perspective = user's Right hand (mirrored).
        """
        result_obj = HandsResult()
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self._detector.detect(mp_image)
        except Exception as e:
            logger.warning("MediaPipe processing error: %s", e)
            return result_obj

        if not result.hand_landmarks:
            return result_obj

        for i, hand_lms in enumerate(result.hand_landmarks):
            landmarks = [
                Landmark(
                    x=lm.x,
                    y=lm.y,
                    z=lm.z,
                    visibility=getattr(lm, "visibility", None) or 0.0,
                )
                for lm in hand_lms
            ]
            # Flip: camera "Left" = user's right hand (webcam is a mirror)
            cam_label = result.handedness[i][0].category_name
            if cam_label == "Left":
                result_obj.right = landmarks
            else:
                result_obj.left = landmarks

        return result_obj

    def close(self) -> None:
        self._detector.close()

    def __enter__(self) -> "HandTracker":
        return self

    def __exit__(self, *_) -> None:
        self.close()
