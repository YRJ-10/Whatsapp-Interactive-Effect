from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CameraConfig:
    index: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30


@dataclass(frozen=True)
class ScreenCropConfig:
    x: int = 100
    y: int = 100
    width: int = 640
    height: int = 360
    backend: str = "auto"


@dataclass(frozen=True)
class GestureConfig:
    enabled: bool = True
    model_path: str = "models/gesture_recognizer.task"
    min_score: float = 0.55
    enable_ok_sign: bool = True
    stable_frames: int = 4
    cooldown_ms: int = 1200


@dataclass(frozen=True)
class EffectsConfig:
    enabled: bool = True
    duration_ms: int = 1400
    confetti_count: int = 70


@dataclass(frozen=True)
class VirtualCameraConfig:
    width: int = 1280
    height: int = 720
    fps: int = 30
    enabled_preview: bool = True


@dataclass(frozen=True)
class PreviewConfig:
    webcam_window_name: str = "WhatsApp Interactive Motion - Webcam Preview"
    crop_window_name: str = "WhatsApp Interactive Motion - WhatsApp Crop Preview"


@dataclass(frozen=True)
class AppConfig:
    camera: CameraConfig = field(default_factory=CameraConfig)
    screen_crop: ScreenCropConfig = field(default_factory=ScreenCropConfig)
    gesture: GestureConfig = field(default_factory=GestureConfig)
    effects: EffectsConfig = field(default_factory=EffectsConfig)
    virtual_camera: VirtualCameraConfig = field(default_factory=VirtualCameraConfig)
    preview: PreviewConfig = field(default_factory=PreviewConfig)


def load_config(path: str | Path = "config.json") -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        return AppConfig()

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    camera = _section(raw, "camera")
    screen_crop = _section(raw, "screen_crop")
    gesture = _section(raw, "gesture")
    effects = _section(raw, "effects")
    virtual_camera = _section(raw, "virtual_camera")
    preview = _section(raw, "preview")

    return AppConfig(
        camera=CameraConfig(
            index=int(camera.get("index", 0)),
            width=int(camera.get("width", 1280)),
            height=int(camera.get("height", 720)),
            fps=int(camera.get("fps", 30)),
        ),
        screen_crop=ScreenCropConfig(
            x=int(screen_crop.get("x", 100)),
            y=int(screen_crop.get("y", 100)),
            width=int(screen_crop.get("width", 640)),
            height=int(screen_crop.get("height", 360)),
            backend=str(screen_crop.get("backend", "auto")),
        ),
        gesture=GestureConfig(
            enabled=_as_bool(gesture.get("enabled", True)),
            model_path=str(gesture.get("model_path", "models/gesture_recognizer.task")),
            min_score=float(gesture.get("min_score", 0.55)),
            enable_ok_sign=_as_bool(gesture.get("enable_ok_sign", True)),
            stable_frames=int(gesture.get("stable_frames", 4)),
            cooldown_ms=int(gesture.get("cooldown_ms", 1200)),
        ),
        effects=EffectsConfig(
            enabled=_as_bool(effects.get("enabled", True)),
            duration_ms=int(effects.get("duration_ms", 1400)),
            confetti_count=int(effects.get("confetti_count", 70)),
        ),
        virtual_camera=VirtualCameraConfig(
            width=int(virtual_camera.get("width", 1280)),
            height=int(virtual_camera.get("height", 720)),
            fps=int(virtual_camera.get("fps", 30)),
            enabled_preview=_as_bool(virtual_camera.get("enabled_preview", True)),
        ),
        preview=PreviewConfig(
            webcam_window_name=str(
                preview.get(
                    "webcam_window_name",
                    "WhatsApp Interactive Motion - Webcam Preview",
                )
            ),
            crop_window_name=str(
                preview.get(
                    "crop_window_name",
                    "WhatsApp Interactive Motion - WhatsApp Crop Preview",
                )
            ),
        ),
    )


def _section(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name, {})
    if not isinstance(value, dict):
        return {}
    return value


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)
