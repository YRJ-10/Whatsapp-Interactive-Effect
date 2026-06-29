from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CameraConfig:
    index: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30


@dataclass(frozen=True)
class PreviewConfig:
    window_name: str = "WhatsApp Interactive Motion - Webcam Preview"


@dataclass(frozen=True)
class AppConfig:
    camera: CameraConfig = CameraConfig()
    preview: PreviewConfig = PreviewConfig()


def load_config(path: str | Path = "config.json") -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        return AppConfig()

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    camera = _section(raw, "camera")
    preview = _section(raw, "preview")

    return AppConfig(
        camera=CameraConfig(
            index=int(camera.get("index", 0)),
            width=int(camera.get("width", 1280)),
            height=int(camera.get("height", 720)),
            fps=int(camera.get("fps", 30)),
        ),
        preview=PreviewConfig(
            window_name=str(
                preview.get(
                    "window_name",
                    "WhatsApp Interactive Motion - Webcam Preview",
                )
            )
        ),
    )


def _section(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name, {})
    if not isinstance(value, dict):
        return {}
    return value
