from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Landmark:
    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class GestureResult:
    name: str
    score: float
    source: str
    landmarks: tuple[Landmark, ...] = ()

    @property
    def display_name(self) -> str:
        return DISPLAY_NAMES.get(self.name, self.name)


NO_GESTURE = GestureResult(name="None", score=0.0, source="none")

DISPLAY_NAMES = {
    "Open_Palm": "Open Palm",
    "Closed_Fist": "Fist",
    "Thumb_Up": "Thumbs Up",
    "Victory": "Victory",
    "OK_Sign": "OK Sign",
    "None": "No Gesture",
}

SUPPORTED_BUILT_IN_GESTURES = {
    "Open_Palm",
    "Closed_Fist",
    "Thumb_Up",
    "Victory",
}
