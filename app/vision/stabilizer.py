from __future__ import annotations

from dataclasses import dataclass

from app.vision.gesture_result import GestureResult


@dataclass(frozen=True)
class GestureEvent:
    gesture: GestureResult
    stable_frames: int
    timestamp_ms: int


@dataclass(frozen=True)
class StabilizerState:
    candidate_name: str = "None"
    candidate_frames: int = 0
    last_event_name: str = "None"
    last_event_ms: int = -1_000_000
    last_event: GestureEvent | None = None


class GestureStabilizer:
    def __init__(self, stable_frames: int, cooldown_ms: int) -> None:
        if stable_frames <= 0:
            raise ValueError("stable_frames must be greater than zero.")
        if cooldown_ms < 0:
            raise ValueError("cooldown_ms must be zero or greater.")

        self.stable_frames = stable_frames
        self.cooldown_ms = cooldown_ms
        self._candidate_name = "None"
        self._candidate_frames = 0
        self._last_event_name = "None"
        self._last_event_ms = -1_000_000
        self._last_event: GestureEvent | None = None

    def update(
        self,
        gesture: GestureResult,
        timestamp_ms: int,
    ) -> GestureEvent | None:
        if gesture.name in {"None", "Unavailable"}:
            self._candidate_name = "None"
            self._candidate_frames = 0
            return None

        if gesture.name == self._candidate_name:
            self._candidate_frames += 1
        else:
            self._candidate_name = gesture.name
            self._candidate_frames = 1

        if self._candidate_frames < self.stable_frames:
            return None

        if not self._cooldown_elapsed(gesture.name, timestamp_ms):
            return None

        event = GestureEvent(
            gesture=gesture,
            stable_frames=self._candidate_frames,
            timestamp_ms=timestamp_ms,
        )
        self._last_event = event
        self._last_event_name = gesture.name
        self._last_event_ms = timestamp_ms
        return event

    def state(self) -> StabilizerState:
        return StabilizerState(
            candidate_name=self._candidate_name,
            candidate_frames=self._candidate_frames,
            last_event_name=self._last_event_name,
            last_event_ms=self._last_event_ms,
            last_event=self._last_event,
        )

    def _cooldown_elapsed(self, gesture_name: str, timestamp_ms: int) -> bool:
        if gesture_name != self._last_event_name:
            return True
        return timestamp_ms - self._last_event_ms >= self.cooldown_ms
