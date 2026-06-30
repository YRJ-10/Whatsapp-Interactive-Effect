from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class VirtualCameraSettings:
    width: int
    height: int
    fps: int
    backend: str = "auto"


class VirtualCameraOutput:
    def __init__(self, settings: VirtualCameraSettings) -> None:
        self.settings = settings
        self._camera: Any = None

    def open(self) -> None:
        if self.settings.width <= 0 or self.settings.height <= 0:
            raise ValueError("Virtual camera width and height must be greater than zero.")
        if self.settings.fps <= 0:
            raise ValueError("Virtual camera FPS must be greater than zero.")

        try:
            import pyvirtualcam
        except ImportError as exc:
            raise RuntimeError(
                "pyvirtualcam is not installed. Run pip install -r requirements.txt."
            ) from exc

        try:
            backend = None if self.settings.backend == "auto" else self.settings.backend
            self._camera = pyvirtualcam.Camera(
                width=self.settings.width,
                height=self.settings.height,
                fps=self.settings.fps,
                backend=backend,
            )
        except Exception as exc:
            raise RuntimeError(
                "Could not open virtual camera. On Windows, install OBS Studio "
                "and enable OBS Virtual Camera support, then try again."
            ) from exc

    def send(self, frame_bgr: np.ndarray) -> None:
        if self._camera is None:
            raise RuntimeError("VirtualCameraOutput is not open.")

        frame = self._fit_frame(frame_bgr)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._camera.send(np.ascontiguousarray(frame_rgb))
        self._camera.sleep_until_next_frame()

    def close(self) -> None:
        if self._camera is not None:
            self._camera.close()
            self._camera = None

    def _fit_frame(self, frame_bgr: np.ndarray) -> np.ndarray:
        height, width = frame_bgr.shape[:2]
        if width == self.settings.width and height == self.settings.height:
            return frame_bgr
        return cv2.resize(
            frame_bgr,
            (self.settings.width, self.settings.height),
            interpolation=cv2.INTER_AREA,
        )

    def __enter__(self) -> VirtualCameraOutput:
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
