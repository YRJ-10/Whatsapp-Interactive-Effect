from __future__ import annotations

import argparse
import time

import cv2

from app.capture.webcam import WebcamCapture, WebcamSettings
from app.config import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 1 webcam preview for WhatsApp Interactive Motion."
    )
    parser.add_argument("--config", default="config.json", help="Path to config file.")
    parser.add_argument("--camera-index", type=int, default=None)
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--fps", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    camera_config = config.camera

    settings = WebcamSettings(
        index=args.camera_index
        if args.camera_index is not None
        else camera_config.index,
        width=args.width if args.width is not None else camera_config.width,
        height=args.height if args.height is not None else camera_config.height,
        fps=args.fps if args.fps is not None else camera_config.fps,
    )

    frame_count = 0
    fps_timer = time.perf_counter()
    measured_fps = 0.0

    print("Starting Phase 1 webcam preview.")
    print("Press q or Esc in the preview window to stop.")

    try:
        with WebcamCapture(settings) as webcam:
            cv2.namedWindow(config.preview.window_name, cv2.WINDOW_NORMAL)

            while True:
                frame = webcam.read()
                frame_count += 1

                now = time.perf_counter()
                elapsed = now - fps_timer
                if elapsed >= 1.0:
                    measured_fps = frame_count / elapsed
                    frame_count = 0
                    fps_timer = now

                _draw_status(frame, measured_fps, settings)
                cv2.imshow(config.preview.window_name, frame)

                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
    finally:
        cv2.destroyAllWindows()

    return 0


def _draw_status(frame, measured_fps: float, settings: WebcamSettings) -> None:
    status = (
        f"Camera {settings.index} | target {settings.width}x{settings.height}"
        f" @ {settings.fps} FPS | measured {measured_fps:.1f} FPS"
    )
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
