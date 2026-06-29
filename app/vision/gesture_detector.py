from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.vision.gesture_result import (
    NO_GESTURE,
    Landmark,
    GestureResult,
    SUPPORTED_BUILT_IN_GESTURES,
)
from app.vision.ok_sign import is_ok_sign


class GestureDetector:
    def __init__(
        self,
        model_path: str,
        min_score: float,
        enable_ok_sign: bool,
    ) -> None:
        self.model_path = Path(model_path)
        self.min_score = min_score
        self.enable_ok_sign = enable_ok_sign
        self._recognizer: Any = None
        self._mp_image: Any = None
        self._timestamp_ms = 0

    def open(self) -> None:
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Gesture model not found: {self.model_path}. "
                "Download gesture_recognizer.task into the models folder."
            )

        try:
            from mediapipe import Image
            from mediapipe import ImageFormat
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
        except ImportError as exc:
            raise RuntimeError(
                "MediaPipe is not installed. Run pip install -r requirements.txt."
            ) from exc

        base_options = python.BaseOptions(model_asset_path=str(self.model_path))
        options = vision.GestureRecognizerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._recognizer = vision.GestureRecognizer.create_from_options(options)
        self._mp_image = (Image, ImageFormat)

    def detect(self, frame_bgr: np.ndarray) -> GestureResult:
        if self._recognizer is None or self._mp_image is None:
            raise RuntimeError("GestureDetector is not open.")

        image_cls, image_format = self._mp_image
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = image_cls(
            image_format=image_format.SRGB,
            data=np.ascontiguousarray(frame_rgb),
        )

        self._timestamp_ms += 33
        result = self._recognizer.recognize_for_video(mp_image, self._timestamp_ms)
        landmarks = _extract_first_hand_landmarks(result)

        built_in = self._extract_built_in_result(result, landmarks)
        if built_in.name != "None":
            return built_in

        if self.enable_ok_sign and is_ok_sign(landmarks):
            return GestureResult(
                name="OK_Sign",
                score=0.75,
                source="landmark_rule",
                landmarks=landmarks,
            )

        if landmarks:
            return GestureResult(
                name="None",
                score=0.0,
                source="landmark_rule",
                landmarks=landmarks,
            )
        return NO_GESTURE

    def close(self) -> None:
        if self._recognizer is not None:
            self._recognizer.close()
        self._recognizer = None

    def _extract_built_in_result(
        self,
        result: Any,
        landmarks: tuple[Landmark, ...],
    ) -> GestureResult:
        if not result.gestures:
            return NO_GESTURE

        top_category = result.gestures[0][0]
        name = top_category.category_name
        score = float(top_category.score)
        if name not in SUPPORTED_BUILT_IN_GESTURES or score < self.min_score:
            return NO_GESTURE

        return GestureResult(
            name=name,
            score=score,
            source="mediapipe",
            landmarks=landmarks,
        )

    def __enter__(self) -> GestureDetector:
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class DisabledGestureDetector:
    def detect(self, frame_bgr: np.ndarray) -> GestureResult:
        return NO_GESTURE

    def close(self) -> None:
        return None


class UnavailableGestureDetector:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def detect(self, frame_bgr: np.ndarray) -> GestureResult:
        return GestureResult(name="Unavailable", score=0.0, source=self.reason)

    def close(self) -> None:
        return None


def create_gesture_detector(
    enabled: bool,
    model_path: str,
    min_score: float,
    enable_ok_sign: bool,
) -> GestureDetector | DisabledGestureDetector | UnavailableGestureDetector:
    if not enabled:
        return DisabledGestureDetector()

    detector = GestureDetector(
        model_path=model_path,
        min_score=min_score,
        enable_ok_sign=enable_ok_sign,
    )
    try:
        detector.open()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        return UnavailableGestureDetector(str(exc))
    return detector


def _extract_first_hand_landmarks(result: Any) -> tuple[Landmark, ...]:
    if not result.hand_landmarks:
        return ()

    landmarks = []
    for landmark in result.hand_landmarks[0]:
        landmarks.append(
            Landmark(
                x=float(landmark.x),
                y=float(landmark.y),
                z=float(getattr(landmark, "z", 0.0)),
            )
        )
    return tuple(landmarks)
