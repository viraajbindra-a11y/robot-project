"""Movement controller for the robot.

This module provides a Movement class that coordinates the left/right motors.
When running on a Raspberry Pi with gpiozero installed we talk to the real
hardware. Otherwise we transparently fall back to a simulation so the rest of
the application can keep running with predictable behaviour.
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
        """Create a Movement controller.

        Args:
            left_pins: (forward_pin, backward_pin) tuple for the left motor.
            right_pins: (forward_pin, backward_pin) tuple for the right motor.
            simulate: Force the software simulation even if gpiozero is present.
            logger: Optional logger. Defaults to a module-level logger.
            sim_step: Distance (in arbitrary units) that corresponds to full
                speed in the simulation. Allows callers to scale the virtual
                motion to match their scenarios.
        """

        if sim_step <= 0:
            raise ValueError("sim_step must be positive")

        self.left_pins = left_pins
        self.right_pins = right_pins

        self._logger = logger or logging.getLogger(__name__)
        self._sim_step = float(sim_step)
        self._last_action: Tuple[str, float] = ("stop", 0.0)

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

    @property
    def is_simulation(self) -> bool:
        return not self._hw

    @property
    def last_action(self) -> Tuple[str, float]:
        """Return the last command issued to the controller."""
        return self._last_action

    def reset(self) -> None:
        """Reset the simulated position/direction to their defaults."""
        self.position = [0.0, 0.0]
        self.direction = 'N'
        self._record_action('reset', 0.0)
        if self.is_simulation:
            self._logger.debug("Simulation reset to origin facing north")

    def move_forward(self, speed: float = 1.0) -> None:
        """Move forward. Speed is clamped between 0 (stop) and 1 (full)."""
        speed = self._clamp_speed(speed)
        self._record_action('forward', speed)
        if self._hw:
            self.left.forward(speed)
            self.right.forward(speed)
        else:
            self._advance_simulation(speed)

    def move_backward(self, speed: float = 1.0) -> None:
        """Move backward."""
        speed = self._clamp_speed(speed)
        self._record_action('backward', speed)
        if self._hw:
            self.left.backward(speed)
            self.right.backward(speed)
        else:
            self._advance_simulation(-speed)

    def turn_left(self, speed: float = 1.0) -> None:
        """Turn left in place: left motor backward, right motor forward."""
        speed = self._clamp_speed(speed)
        self._record_action('turn_left', speed)
        if self._hw:
            self.left.backward(speed)
            self.right.forward(speed)
        else:
            self.direction = _rotate_left(self.direction)
            self._logger.debug("Simulation direction -> %s", self.direction)

    def turn_right(self, speed: float = 1.0) -> None:
        """Turn right in place: left forward, right backward."""
        speed = self._clamp_speed(speed)
        self._record_action('turn_right', speed)
        if self._hw:
            self.left.forward(speed)
            self.right.backward(speed)
        else:
            self.direction = _rotate_right(self.direction)
            self._logger.debug("Simulation direction -> %s", self.direction)

    def stop(self) -> None:
        """Stop both motors."""
        self._record_action('stop', 0.0)
        if self._hw:
            self.left.stop()
            self.right.stop()
        else:
            self._logger.debug("Simulation stop")

    def _record_action(self, action: str, speed: float) -> None:
        self._last_action = (action, speed)

    def _clamp_speed(self, speed: float) -> float:
        if speed < 0:
            raise ValueError("speed must be non-negative")
        clamped = min(float(speed), 1.0)
        if clamped != speed:
            self._logger.debug("Clamped speed from %s to %s", speed, clamped)
        return clamped

    def _advance_simulation(self, scaled_speed: float) -> None:
        distance = self._sim_step * scaled_speed
        dx, dy = _dir_to_delta(self.direction)
        self.position[0] += dx * distance
        self.position[1] += dy * distance
        self._logger.debug(
            "Simulation move -> pos=(%.3f, %.3f) dir=%s",
            self.position[0],
            self.position[1],
            self.direction,
        )
