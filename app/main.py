from __future__ import annotations

import argparse
import time

import cv2

from app.capture.webcam import WebcamCapture, WebcamSettings
from app.capture.whatsapp_crop import ScreenCropCapture, ScreenCropSettings
from app.config import load_config
from app.effects.engine import EffectEngine, EffectsSettings
from app.output.virtual_camera import VirtualCameraOutput, VirtualCameraSettings
from app.vision.gesture_detector import create_gesture_detector
from app.vision.gesture_result import GestureResult, NO_GESTURE
from app.vision.stabilizer import GestureEvent, GestureStabilizer, StabilizerState


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="WhatsApp Interactive Motion MVP preview runner."
    )
    parser.add_argument("--config", default="config.json", help="Path to config file.")
    parser.add_argument(
        "--mode",
        choices=("webcam", "crop", "dual", "virtual"),
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
    parser.add_argument(
        "--disable-gesture-detection",
        action="store_true",
        help="Run crop preview without MediaPipe gesture detection.",
    )
    parser.add_argument("--gesture-model", default=None, help="Path to .task model.")
    parser.add_argument("--gesture-min-score", type=float, default=None)
    parser.add_argument("--stable-frames", type=int, default=None)
    parser.add_argument("--gesture-cooldown-ms", type=int, default=None)
    parser.add_argument(
        "--disable-effects",
        action="store_true",
        help="Run preview without visual effects.",
    )
    parser.add_argument("--effect-duration-ms", type=int, default=None)
    parser.add_argument(
        "--demo-effect",
        choices=("Open_Palm", "Closed_Fist", "Thumb_Up", "Victory", "OK_Sign"),
        default=None,
        help="Trigger one effect at startup for preview testing.",
    )
    parser.add_argument("--virtual-width", type=int, default=None)
    parser.add_argument("--virtual-height", type=int, default=None)
    parser.add_argument("--virtual-fps", type=int, default=None)
    parser.add_argument(
        "--virtual-backend",
        choices=("auto", "obs", "unitycapture"),
        default=None,
    )
    parser.add_argument(
        "--no-virtual-preview",
        action="store_true",
        help="Send to virtual camera without showing local preview windows.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)

    webcam_settings = _webcam_settings_from_args(args, config.camera)
    crop_settings = _crop_settings_from_args(args, config.screen_crop)
    gesture_settings = _gesture_settings_from_args(args, config.gesture)
    effects_settings = _effects_settings_from_args(args, config.effects)
    virtual_settings = _virtual_settings_from_args(args, config.virtual_camera)

    print(f"Starting preview mode: {args.mode}.")
    print("Press q or Esc in the preview window to stop.")

    try:
        if args.mode == "webcam":
            _run_webcam_preview(
                webcam_settings,
                effects_settings,
                args.demo_effect,
                config.preview.webcam_window_name,
            )
        elif args.mode == "crop":
            _run_crop_preview(
                crop_settings,
                gesture_settings,
                config.preview.crop_window_name,
            )
        elif args.mode == "dual":
            _run_dual_preview(
                webcam_settings,
                crop_settings,
                gesture_settings,
                effects_settings,
                args.demo_effect,
                config.preview.webcam_window_name,
                config.preview.crop_window_name,
            )
        else:
            _run_virtual_camera_pipeline(
                webcam_settings,
                crop_settings,
                gesture_settings,
                effects_settings,
                virtual_settings,
                args.demo_effect,
                config.virtual_camera.enabled_preview and not args.no_virtual_preview,
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


def _gesture_settings_from_args(args, gesture_config) -> dict[str, object]:
    return {
        "enabled": bool(gesture_config.enabled)
        and not args.disable_gesture_detection,
        "model_path": args.gesture_model
        if args.gesture_model is not None
        else gesture_config.model_path,
        "min_score": args.gesture_min_score
        if args.gesture_min_score is not None
        else gesture_config.min_score,
        "enable_ok_sign": gesture_config.enable_ok_sign,
        "stable_frames": args.stable_frames
        if args.stable_frames is not None
        else gesture_config.stable_frames,
        "cooldown_ms": args.gesture_cooldown_ms
        if args.gesture_cooldown_ms is not None
        else gesture_config.cooldown_ms,
    }


def _effects_settings_from_args(args, effects_config) -> EffectsSettings:
    return EffectsSettings(
        enabled=bool(effects_config.enabled) and not args.disable_effects,
        duration_ms=args.effect_duration_ms
        if args.effect_duration_ms is not None
        else effects_config.duration_ms,
        confetti_count=effects_config.confetti_count,
    )


def _virtual_settings_from_args(args, virtual_config) -> VirtualCameraSettings:
    return VirtualCameraSettings(
        width=args.virtual_width
        if args.virtual_width is not None
        else virtual_config.width,
        height=args.virtual_height
        if args.virtual_height is not None
        else virtual_config.height,
        fps=args.virtual_fps if args.virtual_fps is not None else virtual_config.fps,
        backend=args.virtual_backend
        if args.virtual_backend is not None
        else virtual_config.backend,
    )


def _run_webcam_preview(
    settings: WebcamSettings,
    effects_settings: EffectsSettings,
    demo_effect: str | None,
    window_name: str,
) -> None:
    fps_meter = FpsMeter()
    effect_engine = EffectEngine(effects_settings)
    demo_triggered = False

    with WebcamCapture(settings) as webcam:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        while True:
            frame = webcam.read()
            now_ms = _now_ms()
            if not demo_triggered:
                _trigger_demo_effect(effect_engine, demo_effect, now_ms)
                demo_triggered = True

            frame = effect_engine.apply(frame, now_ms)
            measured_fps = fps_meter.tick()

            _draw_webcam_status(frame, measured_fps, settings)
            cv2.imshow(window_name, frame)

            if _should_quit():
                break


def _run_crop_preview(
    settings: ScreenCropSettings,
    gesture_settings: dict[str, object],
    window_name: str,
) -> None:
    fps_meter = FpsMeter()
    with ScreenCropCapture(settings) as screen_crop:
        detector = _create_detector_from_settings(gesture_settings)
        stabilizer = _create_stabilizer_from_settings(gesture_settings)
        try:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

            while True:
                frame = screen_crop.read()
                measured_fps = fps_meter.tick()
                gesture = detector.detect(frame)
                event = stabilizer.update(gesture, _now_ms())

                _draw_crop_status(
                    frame,
                    measured_fps,
                    settings,
                    gesture,
                    stabilizer.state(),
                    event,
                )
                cv2.imshow(window_name, frame)

                if _should_quit():
                    break
        finally:
            detector.close()


def _run_dual_preview(
    webcam_settings: WebcamSettings,
    crop_settings: ScreenCropSettings,
    gesture_settings: dict[str, object],
    effects_settings: EffectsSettings,
    demo_effect: str | None,
    webcam_window_name: str,
    crop_window_name: str,
) -> None:
    webcam_fps = FpsMeter()
    crop_fps = FpsMeter()
    effect_engine = EffectEngine(effects_settings)
    demo_triggered = False

    with WebcamCapture(webcam_settings) as webcam:
        with ScreenCropCapture(crop_settings) as screen_crop:
            detector = _create_detector_from_settings(gesture_settings)
            stabilizer = _create_stabilizer_from_settings(gesture_settings)
            try:
                cv2.namedWindow(webcam_window_name, cv2.WINDOW_NORMAL)
                cv2.namedWindow(crop_window_name, cv2.WINDOW_NORMAL)

                while True:
                    webcam_frame = webcam.read()
                    crop_frame = screen_crop.read()
                    now_ms = _now_ms()
                    if not demo_triggered:
                        _trigger_demo_effect(effect_engine, demo_effect, now_ms)
                        demo_triggered = True

                    gesture = detector.detect(crop_frame)
                    event = stabilizer.update(gesture, now_ms)
                    effect_engine.trigger(event)
                    webcam_frame = effect_engine.apply(webcam_frame, now_ms)

                    _draw_webcam_status(
                        webcam_frame,
                        webcam_fps.tick(),
                        webcam_settings,
                    )
                    _draw_crop_status(
                        crop_frame,
                        crop_fps.tick(),
                        crop_settings,
                        gesture,
                        stabilizer.state(),
                        event,
                    )

                    cv2.imshow(webcam_window_name, webcam_frame)
                    cv2.imshow(crop_window_name, crop_frame)

                    if _should_quit():
                        break
            finally:
                detector.close()


def _run_virtual_camera_pipeline(
    webcam_settings: WebcamSettings,
    crop_settings: ScreenCropSettings,
    gesture_settings: dict[str, object],
    effects_settings: EffectsSettings,
    virtual_settings: VirtualCameraSettings,
    demo_effect: str | None,
    enabled_preview: bool,
    webcam_window_name: str,
    crop_window_name: str,
) -> None:
    webcam_fps = FpsMeter()
    crop_fps = FpsMeter()
    effect_engine = EffectEngine(effects_settings)
    demo_triggered = False

    with WebcamCapture(webcam_settings) as webcam:
        with ScreenCropCapture(crop_settings) as screen_crop:
            with VirtualCameraOutput(virtual_settings) as virtual_camera:
                detector = _create_detector_from_settings(gesture_settings)
                stabilizer = _create_stabilizer_from_settings(gesture_settings)
                try:
                    if enabled_preview:
                        cv2.namedWindow(webcam_window_name, cv2.WINDOW_NORMAL)
                        cv2.namedWindow(crop_window_name, cv2.WINDOW_NORMAL)

                    while True:
                        webcam_frame = webcam.read()
                        crop_frame = screen_crop.read()
                        now_ms = _now_ms()
                        if not demo_triggered:
                            _trigger_demo_effect(effect_engine, demo_effect, now_ms)
                            demo_triggered = True

                        gesture = detector.detect(crop_frame)
                        event = stabilizer.update(gesture, now_ms)
                        effect_engine.trigger(event)
                        webcam_frame = effect_engine.apply(webcam_frame, now_ms)
                        output_frame = webcam_frame.copy()

                        _draw_webcam_status(
                            webcam_frame,
                            webcam_fps.tick(),
                            webcam_settings,
                        )
                        _draw_virtual_status(webcam_frame, virtual_settings)
                        _draw_crop_status(
                            crop_frame,
                            crop_fps.tick(),
                            crop_settings,
                            gesture,
                            stabilizer.state(),
                            event,
                        )

                        virtual_camera.send(output_frame)

                        if enabled_preview:
                            cv2.imshow(webcam_window_name, webcam_frame)
                            cv2.imshow(crop_window_name, crop_frame)
                            if _should_quit():
                                break
                finally:
                    detector.close()


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


def _create_detector_from_settings(gesture_settings: dict[str, object]):
    return create_gesture_detector(
        enabled=bool(gesture_settings["enabled"]),
        model_path=str(gesture_settings["model_path"]),
        min_score=float(gesture_settings["min_score"]),
        enable_ok_sign=bool(gesture_settings["enable_ok_sign"]),
    )


def _create_stabilizer_from_settings(
    gesture_settings: dict[str, object],
) -> GestureStabilizer:
    return GestureStabilizer(
        stable_frames=int(gesture_settings["stable_frames"]),
        cooldown_ms=int(gesture_settings["cooldown_ms"]),
    )


def _trigger_demo_effect(
    effect_engine: EffectEngine,
    gesture_name: str | None,
    now_ms: int,
) -> None:
    if gesture_name is None:
        return

    effect_engine.trigger(
        GestureEvent(
            gesture=GestureResult(
                name=gesture_name,
                score=1.0,
                source="demo",
                landmarks=NO_GESTURE.landmarks,
            ),
            stable_frames=1,
            timestamp_ms=now_ms,
        )
    )


def _now_ms() -> int:
    return int(time.perf_counter() * 1000)


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


def _draw_virtual_status(
    frame,
    settings: VirtualCameraSettings,
) -> None:
    status = f"Virtual camera output: {settings.width}x{settings.height} @ {settings.fps} FPS"
    frame_width = frame.shape[1]
    right = min(frame_width - 12, 930)
    cv2.rectangle(frame, (12, 62), (right, 104), (0, 0, 0), thickness=-1)
    cv2.putText(
        frame,
        status,
        (24, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (80, 220, 255),
        2,
        cv2.LINE_AA,
    )


def _draw_crop_status(
    frame,
    measured_fps: float,
    settings: ScreenCropSettings,
    gesture: GestureResult | None = None,
    stabilizer_state: StabilizerState | None = None,
    event: GestureEvent | None = None,
) -> None:
    status = (
        f"Crop x={settings.x} y={settings.y} {settings.width}x{settings.height}"
        f" | {settings.backend} | measured {measured_fps:.1f} FPS"
    )
    _draw_status_bar(frame, status)
    if gesture is not None:
        _draw_gesture_status(frame, gesture, stabilizer_state, event)


def _draw_status_bar(frame, status: str) -> None:
    frame_width = frame.shape[1]
    right = min(frame_width - 12, 930)
    cv2.rectangle(frame, (12, 12), (right, 54), (0, 0, 0), thickness=-1)
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


def _draw_gesture_status(
    frame,
    gesture: GestureResult,
    stabilizer_state: StabilizerState | None,
    event: GestureEvent | None,
) -> None:
    if gesture.name == "Unavailable":
        status = f"Gesture: unavailable | {gesture.source[:80]}"
        color = (64, 220, 255)
    else:
        status = (
            f"Raw: {gesture.display_name}"
            f" | score {gesture.score:.2f} | {gesture.source}"
        )
        color = (64, 255, 64) if gesture.name != "None" else (190, 190, 190)

    frame_width = frame.shape[1]
    right = min(frame_width - 12, 930)
    cv2.rectangle(frame, (12, 62), (right, 104), (0, 0, 0), thickness=-1)
    cv2.putText(
        frame,
        status,
        (24, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        color,
        2,
        cv2.LINE_AA,
    )

    if stabilizer_state is None:
        return

    if event is not None:
        event_label = event.gesture.display_name
    elif stabilizer_state.last_event is not None:
        event_label = stabilizer_state.last_event.gesture.display_name
    else:
        event_label = "None"

    stable_status = (
        f"Stable candidate: {stabilizer_state.candidate_name}"
        f" x{stabilizer_state.candidate_frames}"
        f" | event: {event_label}"
    )
    stable_color = (0, 215, 255) if event is not None else (255, 220, 120)
    cv2.rectangle(frame, (12, 112), (right, 154), (0, 0, 0), thickness=-1)
    cv2.putText(
        frame,
        stable_status,
        (24, 140),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        stable_color,
        2,
        cv2.LINE_AA,
    )


if __name__ == "__main__":
    raise SystemExit(main())
