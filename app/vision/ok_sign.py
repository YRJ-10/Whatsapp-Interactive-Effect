from __future__ import annotations

import math

from app.vision.gesture_result import Landmark


def is_ok_sign(landmarks: tuple[Landmark, ...]) -> bool:
    if len(landmarks) < 21:
        return False

    wrist = landmarks[0]
    middle_mcp = landmarks[9]
    hand_scale = _distance(wrist, middle_mcp)
    if hand_scale <= 0:
        return False

    thumb_tip = landmarks[4]
    index_tip = landmarks[8]
    thumb_index_distance = _distance(thumb_tip, index_tip) / hand_scale

    circle_is_closed = thumb_index_distance < 0.38
    index_is_curled = landmarks[8].y > landmarks[6].y
    middle_is_open = _finger_extended(landmarks, tip=12, pip=10, mcp=9)
    ring_is_open = _finger_extended(landmarks, tip=16, pip=14, mcp=13)
    pinky_is_open = _finger_extended(landmarks, tip=20, pip=18, mcp=17)

    return (
        circle_is_closed
        and index_is_curled
        and middle_is_open
        and ring_is_open
        and pinky_is_open
    )


def _finger_extended(
    landmarks: tuple[Landmark, ...],
    tip: int,
    pip: int,
    mcp: int,
) -> bool:
    return landmarks[tip].y < landmarks[pip].y < landmarks[mcp].y


def _distance(a: Landmark, b: Landmark) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)
