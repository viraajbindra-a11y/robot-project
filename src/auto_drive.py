"""High level autonomous driving loop.

The AutoDriver combines the movement module with the distance sensor wrapper so
we can run a simple obstacle avoidance routine. Designed to run both on actual
hardware and in simulation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from src.movement import Movement
from src.sensors import DistanceSensorWrapper

LOGGER = logging.getLogger(__name__)


@dataclass
class AutoDriveConfig:
    speed: float = 0.6
    reverse_speed: float = 0.4
    obstacle_threshold_cm: float = 25.0
    reverse_duration_s: float = 0.5
    turn_duration_s: float = 0.4
    poll_interval_s: float = 0.1


class AutoDriver:
    def __init__(
        self,
        *,
        movement: Optional[Movement] = None,
        sensor: Optional[DistanceSensorWrapper] = None,
        config: AutoDriveConfig = AutoDriveConfig(),
        logger: Optional[logging.Logger] = None,
        manage_sensor: bool = True,
    ) -> None:
        self.movement = movement or Movement(simulate=True)
        self.sensor = sensor or DistanceSensorWrapper(simulate=self.movement.is_simulation)
        self._manage_sensor = manage_sensor or sensor is None
        self.config = config
        self.logger = logger or LOGGER
        self._running = False

    def step(self) -> None:
        distance = self.sensor.distance_cm
        self.logger.debug("AutoDriver distance=%.2f", distance)
        if distance <= 0:
            self.logger.warning("Distance sensor returned %.2f, ignoring", distance)
            return

        if distance < self.config.obstacle_threshold_cm:
            self._avoid_obstacle()
        else:
            self.movement.move_forward(self.config.speed)

    def _avoid_obstacle(self) -> None:
        self.logger.info("Obstacle detected. Executing avoidance routine.")
        self.movement.move_backward(self.config.reverse_speed)
        time.sleep(self.config.reverse_duration_s)
        self.movement.turn_right(self.config.speed)
        time.sleep(self.config.turn_duration_s)
        self.movement.stop()

    def run(self) -> None:
        self._running = True
        try:
            while self._running:
                self.step()
                time.sleep(self.config.poll_interval_s)
        finally:
            self.movement.stop()

    def stop(self) -> None:
        self._running = False
        self.movement.stop()
        if self._manage_sensor:
            self.sensor.close()
