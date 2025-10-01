"""PWM based motor control utilities.

This complements :mod:`src.movement` by providing a higher resolution control
surface that maps speed values (0..1) to PWM duty cycles when the underlying
motor driver supports it. The module keeps a simulation fallback so the rest of
our stack can run on developer laptops.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

try:  # pragma: no cover - optional dependency
    from gpiozero import Motor
except Exception:  # pragma: no cover - gpiozero is Pi-only
    Motor = None  # type: ignore

LOGGER = logging.getLogger(__name__)


@dataclass
class MotorPins:
    forward: int
    backward: int


class PWMControl:
    """Fine-grained motor speed controller."""

    def __init__(
        self,
        left_pins: MotorPins = MotorPins(forward=17, backward=18),
        right_pins: MotorPins = MotorPins(forward=22, backward=23),
        *,
        simulate: bool = False,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.logger = logger or LOGGER
        self.left_pins = left_pins
        self.right_pins = right_pins
        self._simulate = simulate or Motor is None
        self._left_speed = 0.0
        self._right_speed = 0.0

        if self._simulate:
            self.left_motor = None
            self.right_motor = None
        else:  # pragma: no cover - requires hardware
            self.left_motor = Motor(forward=left_pins.forward, backward=left_pins.backward)
            self.right_motor = Motor(forward=right_pins.forward, backward=right_pins.backward)

    @property
    def speeds(self) -> Tuple[float, float]:
        return self._left_speed, self._right_speed

    def set_speed(self, left: float, right: float) -> None:
        left = self._clamp(left)
        right = self._clamp(right)
        self._left_speed = left
        self._right_speed = right
        if self._simulate:
            self.logger.debug("[SIM] PWM set left=%.2f right=%.2f", left, right)
            return
        assert self.left_motor and self.right_motor
        if left >= 0:
            self.left_motor.forward(abs(left))
        else:
            self.left_motor.backward(abs(left))
        if right >= 0:
            self.right_motor.forward(abs(right))
        else:
            self.right_motor.backward(abs(right))

    def brake(self) -> None:
        self.set_speed(0.0, 0.0)

    def stop(self) -> None:
        self._left_speed = 0.0
        self._right_speed = 0.0
        if self._simulate:
            self.logger.debug("[SIM] PWM stop")
            return
        assert self.left_motor and self.right_motor
        self.left_motor.stop()
        self.right_motor.stop()

    def close(self) -> None:
        if self._simulate:
            return
        assert self.left_motor and self.right_motor
        self.left_motor.close()
        self.right_motor.close()

    @staticmethod
    def _clamp(value: float) -> float:
        if value < -1.0:
            return -1.0
        if value > 1.0:
            return 1.0
        return float(value)
