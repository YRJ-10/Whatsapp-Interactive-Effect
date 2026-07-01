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
    pulse = 0.5 + 0.5 * math.sin(progress * math.pi * 5)
    alpha = _fade(progress)
    thickness = max(3, int(min(width, height) * 0.008))

    overlay = output.copy()
    margin = max(12, int(min(width, height) * 0.035))
    glow_color = (255, 210, 80)
    accent_color = (80, 215, 255)
    white = (255, 255, 255)

    cv2.rectangle(
        overlay,
        (margin, margin),
        (width - margin, height - margin),
        glow_color,
        thickness * 5,
        cv2.LINE_AA,
    )
    cv2.rectangle(
        overlay,
        (margin + thickness * 4, margin + thickness * 4),
        (width - margin - thickness * 4, height - margin - thickness * 4),
        accent_color,
        thickness * 2,
        cv2.LINE_AA,
    )

    corner = max(30, int(min(width, height) * (0.08 + 0.02 * pulse)))
    for x_sign in (1, -1):
        for y_sign in (1, -1):
            x = margin if x_sign == 1 else width - margin
            y = margin if y_sign == 1 else height - margin
            cv2.line(overlay, (x, y), (x + x_sign * corner, y), white, thickness, cv2.LINE_AA)
            cv2.line(overlay, (x, y), (x, y + y_sign * corner), white, thickness, cv2.LINE_AA)

    cv2.addWeighted(overlay, 0.34 * alpha, output, 1.0 - 0.34 * alpha, 0, output)
    return output


def _draw_fist_impact(frame: np.ndarray, progress: float, seed: int) -> np.ndarray:
    rng = random.Random(seed + int(progress * 1000))
    strength = int((1.0 - progress) * 10)
    dx = rng.randint(-strength, strength) if strength > 0 else 0
    dy = rng.randint(-strength, strength) if strength > 0 else 0

    height, width = frame.shape[:2]
    matrix = np.float32([[1, 0, dx], [0, 1, dy]])
    output = cv2.warpAffine(frame, matrix, (width, height), borderMode=cv2.BORDER_REFLECT)

    flash_alpha = max(0.0, 1.0 - progress * 4.0) * 0.22
    if flash_alpha > 0:
        flash = np.full_like(output, (210, 245, 255))
        cv2.addWeighted(flash, flash_alpha, output, 1.0 - flash_alpha, 0, output)

    center = (width // 2, height // 2)
    alpha = _fade(progress)
    for index, scale in enumerate((0.14, 0.22, 0.31)):
        radius = int(min(width, height) * (scale + progress * (0.36 + index * 0.04)))
        ring_alpha = alpha * (0.42 - index * 0.11)
        overlay = output.copy()
        cv2.circle(
            overlay,
            center,
            radius,
            (60, 130, 255),
            max(2, int(min(width, height) * 0.008)),
            cv2.LINE_AA,
        )
        cv2.addWeighted(overlay, ring_alpha, output, 1.0 - ring_alpha, 0, output)
    return output


def _draw_thumbs_up_badge(frame: np.ndarray, progress: float) -> np.ndarray:
    output = frame.copy()
    height, width = output.shape[:2]
    alpha = _fade(progress)
    ease = _ease_out_back(min(1.0, progress * 1.8))
    badge_width = max(170, int(width * 0.23))
    badge_height = max(58, int(height * 0.11))
    x2 = width - int(width * 0.045)
    x1 = x2 - int(badge_width * ease)
    y1 = int(height * (0.72 - 0.08 * progress))
    y2 = y1 + badge_height

    overlay = output.copy()
    shadow = output.copy()
    cv2.rectangle(
        shadow,
        (x1 + 6, y1 + 8),
        (x2 + 6, y2 + 8),
        (0, 0, 0),
        thickness=-1,
    )
    shadow = cv2.GaussianBlur(shadow, (0, 0), sigmaX=8)
    cv2.addWeighted(shadow, 0.16 * alpha, overlay, 1.0, 0, overlay)

    _draw_gradient_rect(overlay, x1, y1, x2, y2, (255, 178, 46), (50, 216, 255))
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 255, 255), 2, cv2.LINE_AA)
    icon_center = (x1 + int(badge_height * 0.42), y1 + badge_height // 2)
    cv2.circle(overlay, icon_center, int(badge_height * 0.28), (255, 255, 255), -1)
    cv2.putText(
        overlay,
        "+",
        (icon_center[0] - 10, icon_center[1] + 11),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (35, 145, 255),
        3,
        cv2.LINE_AA,
    )
    cv2.putText(
        overlay,
        "LIKE",
        (x1 + int(badge_height * 0.86), y1 + int(badge_height * 0.66)),
        cv2.FONT_HERSHEY_SIMPLEX,
        max(0.75, badge_height / 60),
        (255, 255, 255),
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
    colors = [
        (255, 96, 96),
        (70, 220, 255),
        (95, 255, 150),
        (255, 214, 76),
        (235, 120, 255),
    ]
    burst_alpha = _fade(progress)

    overlay = output.copy()
    cv2.circle(
        overlay,
        (width // 2, int(height * 0.32)),
        int(min(width, height) * (0.12 + progress * 0.32)),
        (255, 245, 180),
        max(2, int(min(width, height) * 0.008)),
        cv2.LINE_AA,
    )
    cv2.addWeighted(overlay, 0.22 * burst_alpha, output, 0.78, 0, output)

    for index in range(max(0, count)):
        start_x = rng.randint(0, width)
        drift = int(math.sin(progress * math.pi * 2.4 + index) * rng.randint(20, 90))
        fall = int((height + 120) * progress)
        y = (rng.randint(-height // 2, 0) + fall) % (height + 80) - 40
        x = (start_x + drift) % width
        size = rng.randint(5, 14)
        color = colors[index % len(colors)]
        angle = progress * math.pi * 3 + index
        if index % 3 == 0:
            cv2.circle(output, (x, y), max(2, size // 2), color, -1, cv2.LINE_AA)
        else:
            x2 = x + int(math.cos(angle) * size)
            y2 = y + int(math.sin(angle) * size)
            cv2.line(output, (x, y), (x2, y2), color, max(2, size // 3), cv2.LINE_AA)

    return output


def _draw_ok_ring(frame: np.ndarray, progress: float) -> np.ndarray:
    output = frame.copy()
    height, width = output.shape[:2]
    center = (width // 2, height // 2)
    alpha = _fade(progress)
    base_radius = min(width, height) * 0.16

    overlay = output.copy()
    for index in range(3):
        radius = int(base_radius + min(width, height) * progress * (0.18 + index * 0.06))
        cv2.circle(
            overlay,
            center,
            radius,
            (90, 255, 150),
            max(3, int(min(width, height) * (0.012 - index * 0.002))),
            cv2.LINE_AA,
        )

    glow = overlay.copy()
    cv2.circle(
        glow,
        center,
        int(base_radius * 0.8),
        (60, 255, 170),
        thickness=-1,
    )
    glow = cv2.GaussianBlur(glow, (0, 0), sigmaX=18)
    cv2.addWeighted(glow, 0.14 * alpha, overlay, 1.0, 0, overlay)

    cv2.putText(
        overlay,
        "OK",
        (center[0] - int(base_radius * 0.42), center[1] + int(base_radius * 0.18)),
        cv2.FONT_HERSHEY_SIMPLEX,
        max(1.1, base_radius / 58),
        (235, 255, 242),
        max(3, int(base_radius * 0.08)),
        cv2.LINE_AA,
    )
    cv2.addWeighted(overlay, alpha, output, 1.0 - alpha, 0, output)
    return output


def _fade(progress: float) -> float:
    return max(0.0, min(1.0, math.sin(progress * math.pi)))


def _ease_out_back(value: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (value - 1.0) ** 3 + c1 * (value - 1.0) ** 2


def _draw_gradient_rect(
    frame: np.ndarray,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    left_color: tuple[int, int, int],
    right_color: tuple[int, int, int],
) -> None:
    height, width = frame.shape[:2]
    x1 = max(0, min(width - 1, x1))
    x2 = max(0, min(width, x2))
    y1 = max(0, min(height - 1, y1))
    y2 = max(0, min(height, y2))
    if x2 <= x1 or y2 <= y1:
        return

    rect_width = x2 - x1
    gradient = np.linspace(0.0, 1.0, rect_width, dtype=np.float32)
    left = np.array(left_color, dtype=np.float32)
    right = np.array(right_color, dtype=np.float32)
    row = (left * (1.0 - gradient[:, None]) + right * gradient[:, None]).astype(
        np.uint8
    )
    frame[y1:y2, x1:x2] = np.tile(row[None, :, :], (y2 - y1, 1, 1))
