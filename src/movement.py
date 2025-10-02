"""Movement controller for the robot.

This module provides a Movement class that coordinates the left/right motors.
When running on a Raspberry Pi with gpiozero installed we talk to the real
hardware. Otherwise we transparently fall back to a simulation so the rest of
the application can keep running with predictable behaviour. The controller now
supports runtime speed scaling and trim to fine tune how the motors respond to
high-level commands.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

try:
    from gpiozero import Motor  # type: ignore[reportMissingImports]
except Exception:  # pragma: no cover - best effort import guard
    Motor = None

CARDINAL_DIRECTIONS = ('N', 'E', 'S', 'W')


def _dir_to_delta(direction: str) -> Tuple[int, int]:
    """Convert cardinal direction to (dx, dy)."""
    return {
        'N': (0, 1),
        'E': (1, 0),
        'S': (0, -1),
        'W': (-1, 0),
    }[direction]


def _rotate_left(direction: str) -> str:
    order = ['N', 'W', 'S', 'E']
    return order[(order.index(direction) + 1) % 4]


def _rotate_right(direction: str) -> str:
    order = ['N', 'E', 'S', 'W']
    return order[(order.index(direction) + 1) % 4]


class Movement:
    """High-level motor controller with simulation fallback."""

    def __init__(
        self,
        left_pins: Tuple[int, int] = (17, 18),
        right_pins: Tuple[int, int] = (22, 23),
        simulate: bool = False,
        *,
        logger: Optional[logging.Logger] = None,
        sim_step: float = 1.0,
    ) -> None:
        if sim_step <= 0:
            raise ValueError("sim_step must be positive")

        self.left_pins = left_pins
        self.right_pins = right_pins
        self._logger = logger or logging.getLogger(__name__)
        self._sim_step = float(sim_step)
        self._last_action: Tuple[str, float] = ("stop", 0.0)
        self._speed_scale = 1.0
        self._trim_left = 0.0
        self._trim_right = 0.0

        # Simulation state (used when hardware not present)
        self.position = [0.0, 0.0]
        self.direction = 'N'

        if Motor and not simulate:
            self.left = Motor(forward=left_pins[0], backward=left_pins[1])
            self.right = Motor(forward=right_pins[0], backward=right_pins[1])
            self._hw = True
        else:
            self.left = None
            self.right = None
            self._hw = False

    # ------------------------------------------------------------------ queries

    @property
    def is_simulation(self) -> bool:
        return not self._hw

    @property
    def last_action(self) -> Tuple[str, float]:
        return self._last_action

    @property
    def speed_scale(self) -> float:
        return self._speed_scale

    @property
    def trim(self) -> Tuple[float, float]:
        return self._trim_left, self._trim_right

    # ------------------------------------------------------------------ actions

    def reset(self) -> None:
        self.position = [0.0, 0.0]
        self.direction = 'N'
        self._record_action('reset', 0.0)
        if self.is_simulation:
            self._logger.debug("Simulation reset to origin facing north")

    def move_forward(self, speed: float = 1.0) -> None:
        speed = self._clamp_positive(speed)
        self._record_action('forward', speed)
        left, right = self._apply_scaling(speed, speed)
        self._drive(left, right)
        if not self._hw:
            self._advance_translation((left + right) / 2.0)

    def move_backward(self, speed: float = 1.0) -> None:
        speed = self._clamp_positive(speed)
        self._record_action('backward', speed)
        left, right = self._apply_scaling(-speed, -speed)
        self._drive(left, right)
        if not self._hw:
            self._advance_translation((left + right) / 2.0)

    def turn_left(self, speed: float = 1.0) -> None:
        speed = self._clamp_positive(speed)
        self._record_action('turn_left', speed)
        left, right = self._apply_scaling(-speed, speed)
        self._drive(left, right)
        if not self._hw:
            self.direction = _rotate_left(self.direction)
            self._logger.debug("Simulation direction -> %s", self.direction)

    def turn_right(self, speed: float = 1.0) -> None:
        speed = self._clamp_positive(speed)
        self._record_action('turn_right', speed)
        left, right = self._apply_scaling(speed, -speed)
        self._drive(left, right)
        if not self._hw:
            self.direction = _rotate_right(self.direction)
            self._logger.debug("Simulation direction -> %s", self.direction)

    def stop(self) -> None:
        self._record_action('stop', 0.0)
        self._drive(0.0, 0.0)
        if not self._hw:
            self._logger.debug("Simulation stop")

    # ------------------------------------------------------------------ tuning

    def set_speed_scale(self, value: float) -> None:
        self._speed_scale = max(0.1, min(2.0, float(value)))
        self._logger.info("Speed scale set to %.2f", self._speed_scale)

    def adjust_speed_scale(self, delta: float) -> None:
        self.set_speed_scale(self._speed_scale + delta)

    def set_trim(self, left: float, right: float) -> None:
        self._trim_left = self._clamp_trim(left)
        self._trim_right = self._clamp_trim(right)
        self._logger.info("Motor trim set to left=%.2f right=%.2f", self._trim_left, self._trim_right)

    def adjust_trim(self, left_delta: float = 0.0, right_delta: float = 0.0) -> None:
        self.set_trim(self._trim_left + left_delta, self._trim_right + right_delta)

    def reset_trim(self) -> None:
        self.set_trim(0.0, 0.0)

    # ------------------------------------------------------------------ helpers

    def _record_action(self, action: str, speed: float) -> None:
        self._last_action = (action, speed)

    def _clamp_positive(self, speed: float) -> float:
        if speed < 0:
            raise ValueError("speed must be non-negative")
        return min(float(speed), 1.0)

    def _apply_scaling(self, left: float, right: float) -> Tuple[float, float]:
        return (
            self._apply_single(left, self._trim_left),
            self._apply_single(right, self._trim_right),
        )

    def _apply_single(self, value: float, trim: float) -> float:
        scaled = value * self._speed_scale
        if value >= 0:
            scaled += trim
            scaled = max(0.0, scaled)
        else:
            scaled -= trim
            scaled = min(0.0, scaled)
        return self._clamp_drive(scaled)

    def _drive(self, left: float, right: float) -> None:
        if self._hw:
            if left >= 0:
                self.left.forward(left)
            else:
                self.left.backward(-left)
            if right >= 0:
                self.right.forward(right)
            else:
                self.right.backward(-right)
        else:
            self._logger.debug("[SIM] drive left=%.2f right=%.2f", left, right)

    def _advance_translation(self, effective_speed: float) -> None:
        distance = self._sim_step * effective_speed
        dx, dy = _dir_to_delta(self.direction)
        self.position[0] += dx * distance
        self.position[1] += dy * distance
        self._logger.debug(
            "Simulation move -> pos=(%.3f, %.3f) dir=%s",
            self.position[0],
            self.position[1],
            self.direction,
        )

    @staticmethod
    def _clamp_trim(value: float) -> float:
        return max(-0.5, min(0.5, float(value)))

    @staticmethod
    def _clamp_drive(value: float) -> float:
        return max(-1.0, min(1.0, float(value)))
