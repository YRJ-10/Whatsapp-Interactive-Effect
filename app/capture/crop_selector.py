from __future__ import annotations

from dataclasses import replace

import cv2
import numpy as np

from app.capture.whatsapp_crop import ScreenCropSettings


def select_screen_crop(settings: ScreenCropSettings) -> ScreenCropSettings:
    screenshot, left, top = _capture_virtual_screen()
    window_name = "Select WhatsApp Caller Area"

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
    cv2.imshow(window_name, screenshot)
    print("Drag area video lawan bicara, lalu tekan Enter atau Space.")
    print("Tekan Esc kalau batal.")

    x, y, width, height = cv2.selectROI(
        window_name,
        screenshot,
        showCrosshair=True,
        fromCenter=False,
    )
    cv2.destroyWindow(window_name)

    if width <= 0 or height <= 0:
        raise RuntimeError("Crop selection cancelled.")

    selected = replace(
        settings,
        x=left + int(x),
        y=top + int(y),
        width=int(width),
        height=int(height),
    )
    print(
        "Selected crop: "
        f"x={selected.x}, y={selected.y}, "
        f"width={selected.width}, height={selected.height}"
    )
    return selected


def _capture_virtual_screen() -> tuple[np.ndarray, int, int]:
    try:
        import mss
    except ImportError as exc:
        raise RuntimeError("mss is required for --select-crop.") from exc

    with mss.mss() as capture:
        monitor = capture.monitors[0]
        screenshot = capture.grab(monitor)
        bgra = np.asarray(screenshot)
        frame = cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)
        return frame, int(monitor["left"]), int(monitor["top"])
