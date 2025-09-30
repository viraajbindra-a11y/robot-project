"""Sensor utilities for the robot.

Currently provides an ultrasonic distance sensor abstraction using
gpiozero.DistanceSensor when available, with a simulation fallback for
development machines.
"""

import time
from typing import Optional

try:
    from gpiozero import DistanceSensor  # type: ignore[reportMissingImports]
except Exception:
    DistanceSensor = None  # type: ignore


class UltrasonicSensor:
    """Simple distance sensor wrapper.

    When running on a Raspberry Pi with gpiozero installed, pass the
    echo and trigger pins (BCM numbering) to use the hardware sensor.
    In simulation mode, readings are synthesized.
    """

    def __init__(self, echo: Optional[int] = None, trigger: Optional[int] = None, simulate: bool = False):
        self._simulate = simulate or not bool(DistanceSensor and echo is not None and trigger is not None)
        self._sim_value_cm: Optional[float] = None
        self._start = time.monotonic()
        if not self._simulate:
            # gpiozero DistanceSensor expects trigger then echo
            self._sensor = DistanceSensor(trigger=trigger, echo=echo, max_distance=2.0)  # ~2m
        else:
            self._sensor = None

    def set_simulated_distance(self, cm: Optional[float]):
        """Override the simulated distance (cm). None restores auto pattern."""
        self._sim_value_cm = cm

    def read_distance_cm(self) -> Optional[float]:
        """Return distance in centimeters, or None if unavailable."""
        if self._simulate:
            if self._sim_value_cm is not None:
                return max(0.0, float(self._sim_value_cm))
            # Generate a simple repeating pattern: far -> near -> far
            t = (time.monotonic() - self._start) % 8.0  # 8s cycle
            if t < 2.0:
                return 120.0  # clear
            elif t < 4.0:
                # approach obstacle
                return 120.0 - (t - 2.0) * 40.0  # down to ~40cm
            elif t < 6.0:
                return 20.0  # close obstacle
            else:
                return 80.0  # clearing again
        # Hardware: gpiozero reports distance in meters
        try:
            meters = self._sensor.distance  # type: ignore[attr-defined]
            return meters * 100.0
        except Exception:
            return None
