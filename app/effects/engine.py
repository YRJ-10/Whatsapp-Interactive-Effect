from __future__ import annotations

import math
import random
from dataclasses import dataclass

import cv2
import numpy as np

from app.vision.stabilizer import GestureEvent


@dataclass(frozen=True)
class EffectsSettings:
    enabled: bool = True
    duration_ms: int = 1400
    confetti_count: int = 70


@dataclass
class ActiveEffect:
    name: str
    started_ms: int
    duration_ms: int
    seed: int


class EffectEngine:
    def __init__(self, settings: EffectsSettings) -> None:
        self.settings = settings
        self._active: list[ActiveEffect] = []

    def trigger(self, event: GestureEvent | None) -> None:
        if not self.settings.enabled or event is None:
            return

        self._active.append(
            ActiveEffect(
                name=event.gesture.name,
                started_ms=event.timestamp_ms,
                duration_ms=self.settings.duration_ms,
                seed=event.timestamp_ms,
            )
        )

    def apply(self, frame: np.ndarray, now_ms: int) -> np.ndarray:
        if not self.settings.enabled:
            return frame

        output = frame
        next_active = []
        for effect in self._active:
            progress = (now_ms - effect.started_ms) / effect.duration_ms
            if progress < 0.0:
                next_active.append(effect)
                continue
            if progress > 1.0:
                continue

            output = self._apply_one(output, effect, progress)
            next_active.append(effect)

        self._active = next_active
        return output

    def _apply_one(
        self,
        frame: np.ndarray,
        effect: ActiveEffect,
        progress: float,
    ) -> np.ndarray:
        if effect.name == "Open_Palm":
            return _draw_open_palm_glow(frame, progress)
        if effect.name == "Closed_Fist":
            return _draw_fist_impact(frame, progress, effect.seed)
        if effect.name == "Thumb_Up":
            return _draw_thumbs_up_badge(frame, progress)
        if effect.name == "Victory":
            return _draw_victory_confetti(
                frame,
                progress,
                effect.seed,
                self.settings.confetti_count,
            )
        if effect.name == "OK_Sign":
            return _draw_ok_ring(frame, progress)
        return frame


def _draw_open_palm_glow(frame: np.ndarray, progress: float) -> np.ndarray:
    output = frame.copy()
    height, width = output.shape[:2]
    pulse = 0.5 + 0.5 * math.sin(progress * math.pi * 6)
    alpha = _fade(progress) * (0.35 + 0.35 * pulse)
    color = (255, 190, 60)
    thickness = max(8, int(min(width, height) * 0.025))

    overlay = output.copy()
    cv2.rectangle(
        overlay,
        (thickness, thickness),
        (width - thickness, height - thickness),
        color,
        thickness * 2,
    )
    cv2.addWeighted(overlay, alpha, output, 1.0 - alpha, 0, output)
    return output


def _draw_fist_impact(frame: np.ndarray, progress: float, seed: int) -> np.ndarray:
    rng = random.Random(seed + int(progress * 1000))
    strength = int((1.0 - progress) * 16)
    dx = rng.randint(-strength, strength) if strength > 0 else 0
    dy = rng.randint(-strength, strength) if strength > 0 else 0

    height, width = frame.shape[:2]
    matrix = np.float32([[1, 0, dx], [0, 1, dy]])
    output = cv2.warpAffine(frame, matrix, (width, height), borderMode=cv2.BORDER_REFLECT)

    alpha = max(0.0, 1.0 - progress * 3.0) * 0.45
    if alpha > 0:
        flash = np.full_like(output, (255, 255, 255))
        cv2.addWeighted(flash, alpha, output, 1.0 - alpha, 0, output)

    radius = int(min(width, height) * (0.12 + progress * 0.35))
    cv2.circle(output, (width // 2, height // 2), radius, (40, 40, 255), 5)
    return output


def _draw_thumbs_up_badge(frame: np.ndarray, progress: float) -> np.ndarray:
    output = frame.copy()
    height, width = output.shape[:2]
    alpha = _fade(progress)
    y = int(height * (0.78 - 0.18 * progress))
    center = (int(width * 0.82), y)
    radius = max(42, int(min(width, height) * 0.09))

    overlay = output.copy()
    cv2.circle(overlay, center, radius, (40, 180, 255), thickness=-1)
    cv2.circle(overlay, center, radius, (255, 255, 255), thickness=4)
    cv2.putText(
        overlay,
        "LIKE",
        (center[0] - radius + 11, center[1] + 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        max(0.8, radius / 58),
        (30, 30, 30),
        3,
        cv2.LINE_AA,
    )
    cv2.addWeighted(overlay, alpha, output, 1.0 - alpha, 0, output)
    return output


def _draw_victory_confetti(
    frame: np.ndarray,
    progress: float,
    seed: int,
    count: int,
) -> np.ndarray:
    output = frame.copy()
    height, width = output.shape[:2]
    rng = random.Random(seed)
    colors = [(255, 80, 80), (80, 220, 255), (90, 255, 130), (255, 220, 70)]

    for index in range(max(0, count)):
        start_x = rng.randint(0, width)
        drift = int(math.sin(progress * math.pi * 2 + index) * 45)
        fall = int((height + 80) * progress)
        y = (rng.randint(-height // 2, 0) + fall) % (height + 80) - 40
        x = (start_x + drift) % width
        size = rng.randint(5, 12)
        color = colors[index % len(colors)]
        cv2.rectangle(output, (x, y), (x + size, y + size // 2), color, -1)

    return output


def _draw_ok_ring(frame: np.ndarray, progress: float) -> np.ndarray:
    output = frame.copy()
    height, width = output.shape[:2]
    center = (width // 2, height // 2)
    radius = int(min(width, height) * (0.12 + progress * 0.25))
    alpha = _fade(progress)

    overlay = output.copy()
    cv2.circle(overlay, center, radius, (70, 255, 120), thickness=8)
    cv2.circle(overlay, center, max(8, radius // 3), (70, 255, 120), thickness=4)
    cv2.putText(
        overlay,
        "OK",
        (center[0] - 42, center[1] + 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.7,
        (230, 255, 235),
        5,
        cv2.LINE_AA,
    )
    cv2.addWeighted(overlay, alpha, output, 1.0 - alpha, 0, output)
    return output


def _fade(progress: float) -> float:
    return max(0.0, min(1.0, math.sin(progress * math.pi)))
