from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class WebcamSettings:
    index: int
    width: int
    height: int
    fps: int


class WebcamCapture:
    def __init__(self, settings: WebcamSettings) -> None:
        self.settings = settings
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        capture = cv2.VideoCapture(self.settings.index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            capture = cv2.VideoCapture(self.settings.index)

        if not capture.isOpened():
            raise RuntimeError(
                f"Could not open webcam with index {self.settings.index}."
            )

        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.height)
        capture.set(cv2.CAP_PROP_FPS, self.settings.fps)
        self._capture = capture

        actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = capture.get(cv2.CAP_PROP_FPS)
        print(
            "Webcam opened: "
            f"index={self.settings.index}, "
            f"{actual_width}x{actual_height}, "
            f"fps={actual_fps:.1f}"
        )

    def read(self) -> np.ndarray:
        if self._capture is None:
            raise RuntimeError("WebcamCapture is not open.")

        ok, frame = self._capture.read()
        if not ok or frame is None:
            raise RuntimeError("Could not read frame from webcam.")
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> WebcamCapture:
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
