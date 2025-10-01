"""Simple gripper controller for WALL·E style arms."""

from __future__ import annotations

import logging
from typing import Optional

try:  # pragma: no cover - optional dependency only available on Pi
    from gpiozero import Servo
except Exception:  # pragma: no cover
    Servo = None  # type: ignore

LOGGER = logging.getLogger(__name__)

# Servo value range is -1 (fully backward) to 1 (fully forward).
# Assume -0.8 is open, 0.8 is closed for a typical hobby servo driving a gripper.
DEFAULT_OPEN_VALUE = -0.8
DEFAULT_CLOSE_VALUE = 0.8


class GripperController:
    """Drives a single servo-based gripper with open/close helpers."""

    def __init__(
        self,
        pin: Optional[int],
        *,
        simulate: bool = False,
        open_value: float = DEFAULT_OPEN_VALUE,
        close_value: float = DEFAULT_CLOSE_VALUE,
    ) -> None:
        self.simulate = simulate or Servo is None or pin is None
        self.open_value = max(-1.0, min(1.0, open_value))
        self.close_value = max(-1.0, min(1.0, close_value))
        self._last_value = self.open_value
        self._servo = None
        if not self.simulate and Servo is not None:
            try:  # pragma: no cover - hardware specific
                self._servo = Servo(pin)
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("Failed to initialise gripper servo, falling back to simulation: %s", exc)
                self.simulate = True
        self.open()

    def open(self) -> None:
        LOGGER.info("Opening gripper")
        self._set_value(self.open_value)

    def close(self) -> None:
        LOGGER.info("Closing gripper")
        self._set_value(self.close_value)

    def toggle(self) -> None:
        if self._last_value == self.close_value:
            self.open()
        else:
            self.close()

    def _set_value(self, value: float) -> None:
        clamped = max(-1.0, min(1.0, value))
        self._last_value = clamped
        if self.simulate:
            LOGGER.debug("[SIM] Gripper value=%s", clamped)
            return
        if self._servo is not None:
            self._servo.value = clamped

    def close_controller(self) -> None:
        self.open()
        if self._servo is not None:
            self._servo.close()
