"""Wall proximity guard that keeps the robot from running into obstacles."""

from __future__ import annotations

import logging
from typing import Optional

from src.sensors import DistanceSensorWrapper

LOGGER = logging.getLogger(__name__)


class WallGuard:
    """Monitors a distance sensor and decides when forward motion is unsafe."""

    def __init__(
        self,
        sensor: DistanceSensorWrapper,
        *,
        stop_threshold_cm: float = 20.0,
        resume_threshold_cm: float = 25.0,
    ) -> None:
        if resume_threshold_cm <= stop_threshold_cm:
            raise ValueError("resume_threshold_cm must be greater than stop_threshold_cm")
        self._sensor = sensor
        self._stop = stop_threshold_cm
        self._resume = resume_threshold_cm
        self._blocked = False
        self._last_distance = -1.0

    @property
    def last_distance(self) -> float:
        return self._last_distance

    def _read(self) -> float:
        distance = self._sensor.distance_cm
        self._last_distance = distance
        if distance < 0:
            LOGGER.debug("WallGuard: sensor returned negative distance; assuming clear path")
            return distance
        if distance <= self._stop:
            if not self._blocked:
                LOGGER.info("WallGuard: obstacle detected at %.1f cm", distance)
            self._blocked = True
        elif distance >= self._resume:
            if self._blocked:
                LOGGER.info("WallGuard: path clear (%.1f cm)", distance)
            self._blocked = False
        return distance

    def allows_forward(self) -> bool:
        distance = self._read()
        if distance < 0:
            return True
        return not self._blocked

    def close(self) -> None:
        self._sensor.close()
