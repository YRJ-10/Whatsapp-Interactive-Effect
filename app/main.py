from __future__ import annotations

import argparse
import time

import cv2

from app.capture.webcam import WebcamCapture, WebcamSettings
from app.capture.whatsapp_crop import ScreenCropCapture, ScreenCropSettings
from app.config import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="WhatsApp Interactive Motion MVP preview runner."
    )
    parser.add_argument("--config", default="config.json", help="Path to config file.")
    parser.add_argument(
        "--mode",
        choices=("webcam", "crop", "dual"),
        default="webcam",
        help="Preview mode to run.",
    )
    parser.add_argument("--camera-index", type=int, default=None)
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--fps", type=int, default=None)
    parser.add_argument("--crop-x", type=int, default=None)
    parser.add_argument("--crop-y", type=int, default=None)
    parser.add_argument("--crop-width", type=int, default=None)
    parser.add_argument("--crop-height", type=int, default=None)
    parser.add_argument(
        "--crop-backend",
        choices=("auto", "dxcam", "mss"),
        default=None,
        help="Screen capture backend. 'auto' tries dxcam first, then mss.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)

    webcam_settings = _webcam_settings_from_args(args, config.camera)
    crop_settings = _crop_settings_from_args(args, config.screen_crop)

    print(f"Starting preview mode: {args.mode}.")
    print("Press q or Esc in the preview window to stop.")

    try:
        if args.mode == "webcam":
            _run_webcam_preview(webcam_settings, config.preview.webcam_window_name)
        elif args.mode == "crop":
            _run_crop_preview(crop_settings, config.preview.crop_window_name)
        else:
            _run_dual_preview(
                webcam_settings,
                crop_settings,
                config.preview.webcam_window_name,
                config.preview.crop_window_name,
            )
    finally:
        cv2.destroyAllWindows()

    return 0


def _webcam_settings_from_args(args, camera_config) -> WebcamSettings:
    return WebcamSettings(
        index=args.camera_index
        if args.camera_index is not None
        else camera_config.index,
        width=args.width if args.width is not None else camera_config.width,
        height=args.height if args.height is not None else camera_config.height,
        fps=args.fps if args.fps is not None else camera_config.fps,
    )


def _crop_settings_from_args(args, crop_config) -> ScreenCropSettings:
    return ScreenCropSettings(
        x=args.crop_x if args.crop_x is not None else crop_config.x,
        y=args.crop_y if args.crop_y is not None else crop_config.y,
        width=args.crop_width if args.crop_width is not None else crop_config.width,
        height=args.crop_height if args.crop_height is not None else crop_config.height,
        backend=args.crop_backend
        if args.crop_backend is not None
        else crop_config.backend,
    )


def _run_webcam_preview(settings: WebcamSettings, window_name: str) -> None:
    fps_meter = FpsMeter()
    with WebcamCapture(settings) as webcam:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        while True:
            frame = webcam.read()
            measured_fps = fps_meter.tick()

            _draw_webcam_status(frame, measured_fps, settings)
            cv2.imshow(window_name, frame)

            if _should_quit():
                break


def _run_crop_preview(settings: ScreenCropSettings, window_name: str) -> None:
    fps_meter = FpsMeter()
    with ScreenCropCapture(settings) as screen_crop:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        while True:
            frame = screen_crop.read()
            measured_fps = fps_meter.tick()

            _draw_crop_status(frame, measured_fps, settings)
            cv2.imshow(window_name, frame)

            if _should_quit():
                break


def _run_dual_preview(
    webcam_settings: WebcamSettings,
    crop_settings: ScreenCropSettings,
    webcam_window_name: str,
    crop_window_name: str,
) -> None:
    webcam_fps = FpsMeter()
    crop_fps = FpsMeter()

    with WebcamCapture(webcam_settings) as webcam:
        with ScreenCropCapture(crop_settings) as screen_crop:
            cv2.namedWindow(webcam_window_name, cv2.WINDOW_NORMAL)
            cv2.namedWindow(crop_window_name, cv2.WINDOW_NORMAL)

            while True:
                webcam_frame = webcam.read()
                crop_frame = screen_crop.read()

                _draw_webcam_status(
                    webcam_frame,
                    webcam_fps.tick(),
                    webcam_settings,
                )
                _draw_crop_status(crop_frame, crop_fps.tick(), crop_settings)

                cv2.imshow(webcam_window_name, webcam_frame)
                cv2.imshow(crop_window_name, crop_frame)

                if _should_quit():
                    break


class FpsMeter:
    def __init__(self) -> None:
        self._frame_count = 0
        self._timer = time.perf_counter()
        self._measured_fps = 0.0

    def tick(self) -> float:
        self._frame_count += 1
        now = time.perf_counter()
        elapsed = now - self._timer
        if elapsed >= 1.0:
            self._measured_fps = self._frame_count / elapsed
            self._frame_count = 0
            self._timer = now
        return self._measured_fps


def _should_quit() -> bool:
    key = cv2.waitKey(1) & 0xFF
    return key in (ord("q"), 27)


def _draw_webcam_status(
    frame,
    measured_fps: float,
    settings: WebcamSettings,
) -> None:
    status = (
        f"Camera {settings.index} | target {settings.width}x{settings.height}"
        f" @ {settings.fps} FPS | measured {measured_fps:.1f} FPS"
    )
    _draw_status_bar(frame, status)


def _draw_crop_status(
    frame,
    measured_fps: float,
    settings: ScreenCropSettings,
) -> None:
    status = (
        f"Crop x={settings.x} y={settings.y} {settings.width}x{settings.height}"
        f" | {settings.backend} | measured {measured_fps:.1f} FPS"
    )
    _draw_status_bar(frame, status)


def _draw_status_bar(frame, status: str) -> None:
    cv2.rectangle(frame, (12, 12), (930, 54), (0, 0, 0), thickness=-1)
    cv2.putText(
        frame,
        status,
        (24, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )


if __name__ == "__main__":
    raise SystemExit(main())
