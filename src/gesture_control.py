"""Servo gesture controller used by the chatbot-driven master loop."""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional

try:  # pragma: no cover - optional dependency
    from gpiozero import Servo
except Exception:  # pragma: no cover
    Servo = None  # type: ignore

LOGGER = logging.getLogger(__name__)

DEFAULT_GESTURES: Dict[str, tuple[float, float]] = {
    'rest': (0.0, 0.0),
    'wave': (0.6, -0.6),
    'point': (-0.7, 0.7),
    'nod': (0.2, 0.2),
    'salute': (0.8, -0.2),
}


class GestureController:
    """Drive two arm/hand servos with simple named poses."""

    def __init__(
        self,
        left_servo_pin: Optional[int] = None,
        right_servo_pin: Optional[int] = None,
        *,
        simulate: bool = False,
    ) -> None:
        self.simulate = simulate or Servo is None or left_servo_pin is None or right_servo_pin is None
        self.left_servo = None
        self.right_servo = None
        self._current_left = 0.0
        self._current_right = 0.0
        if not self.simulate and Servo:
            try:  # pragma: no cover - hardware specific
                self.left_servo = Servo(left_servo_pin)
                self.right_servo = Servo(right_servo_pin)
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("Failed to initialise servos, falling back to simulation: %s", exc)
                self.simulate = True
        self.perform('rest')

    @property
    def available_gestures(self) -> Dict[str, tuple[float, float]]:
        return DEFAULT_GESTURES

    def perform(self, gesture: str) -> None:
        gesture = gesture.lower()
        if gesture not in DEFAULT_GESTURES:
            LOGGER.info("Unknown gesture '%s'; defaulting to rest", gesture)
            gesture = 'rest'
        LOGGER.info("Executing gesture: %s", gesture)
        target = DEFAULT_GESTURES[gesture]
        self._set_positions(*target)
        if gesture == 'wave' and not self.simulate:
            self._set_positions(target[0] * 0.7, target[1] * 0.7)
            time.sleep(0.2)
            self._set_positions(*target)

    def set_positions(self, left: float, right: float) -> None:
        """Directly command servo positions (-1..1)."""
        self._set_positions(left, right)

    def adjust(self, left_delta: float = 0.0, right_delta: float = 0.0) -> None:
        """Apply deltas to the current servo positions."""
        self._set_positions(self._current_left + left_delta, self._current_right + right_delta)

    @property
    def positions(self) -> tuple[float, float]:
        return self._current_left, self._current_right

    def _set_positions(self, left: float, right: float) -> None:
        if self.simulate:
            LOGGER.debug("[SIM] Servo positions left=%s right=%s", left, right)
        else:
            if self.left_servo is not None:
                self.left_servo.value = max(-1.0, min(1.0, left))
            if self.right_servo is not None:
                self.right_servo.value = max(-1.0, min(1.0, right))
        self._current_left = max(-1.0, min(1.0, left))
        self._current_right = max(-1.0, min(1.0, right))

    def close(self) -> None:
        self.perform('rest')
        if self.left_servo:
            self.left_servo.close()
        if self.right_servo:
            self.right_servo.close()
