from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class ScreenCropSettings:
    x: int
    y: int
    width: int
    height: int
    backend: str = "auto"


class ScreenCropCapture:
    def __init__(self, settings: ScreenCropSettings) -> None:
        self.settings = settings
        self._backend = ""
        self._dxcam_camera: Any = None
        self._mss_capture: Any = None

    def open(self) -> None:
        if self.settings.width <= 0 or self.settings.height <= 0:
            raise ValueError("Screen crop width and height must be greater than zero.")

        requested = self.settings.backend.lower()
        if requested not in {"auto", "dxcam", "mss"}:
            raise ValueError("Screen crop backend must be 'auto', 'dxcam', or 'mss'.")

        if requested in {"auto", "dxcam"} and self._try_open_dxcam():
            return

        if requested in {"auto", "mss"} and self._try_open_mss():
            return

        raise RuntimeError(
            "Could not open screen capture. Install dxcam or mss, then try again."
        )

    def read(self) -> np.ndarray:
        if self._backend == "dxcam":
            return self._read_dxcam()
        if self._backend == "mss":
            return self._read_mss()
        raise RuntimeError("ScreenCropCapture is not open.")

    def close(self) -> None:
        if self._mss_capture is not None:
            self._mss_capture.close()
        self._dxcam_camera = None
        self._mss_capture = None
        self._backend = ""

    def _try_open_dxcam(self) -> bool:
        try:
            import dxcam
        except ImportError:
            return False

        camera = dxcam.create(output_color="BGR")
        if camera is None:
            return False

        self._dxcam_camera = camera
        self._backend = "dxcam"
        return True

    def _try_open_mss(self) -> bool:
        try:
            import mss
        except ImportError:
            return False

        self._mss_capture = mss.mss()
        self._backend = "mss"
        return True

    def _read_dxcam(self) -> np.ndarray:
        frame = self._dxcam_camera.grab(region=self._region_tuple())
        if frame is None:
            raise RuntimeError("Could not read frame from dxcam screen crop.")
        return frame

    def _read_mss(self) -> np.ndarray:
        screenshot = self._mss_capture.grab(self._monitor_dict())
        bgra = np.asarray(screenshot)
        return cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)

    def _region_tuple(self) -> tuple[int, int, int, int]:
        left = self.settings.x
        top = self.settings.y
        right = left + self.settings.width
        bottom = top + self.settings.height
        return left, top, right, bottom

    def _monitor_dict(self) -> dict[str, int]:
        return {
            "left": self.settings.x,
            "top": self.settings.y,
            "width": self.settings.width,
            "height": self.settings.height,
        }

    def __enter__(self) -> ScreenCropCapture:
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
