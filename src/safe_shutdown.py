"""Utilities for safe motor stop and Raspberry Pi shutdown."""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

from src.battery_check import BatteryMonitor
from src.movement import Movement

LOGGER = logging.getLogger(__name__)


class SafeShutdown:
    def __init__(self, monitor: BatteryMonitor, *, movement: Optional[Movement] = None, logger: Optional[logging.Logger] = None, simulate: bool = False) -> None:
        self.monitor = monitor
        self.movement = movement or Movement(simulate=True)
        self.logger = logger or LOGGER
        self.simulate = simulate
        self._shutdown_initiated = False

    def check_once(self) -> str:
        status = self.monitor.classify()
        voltage = self.monitor.voltage or 0.0
        if status == "critical" and not self._shutdown_initiated:
            self._initiate_shutdown(voltage)
        elif status == "low":
            self.logger.warning("Battery low: %.2fV", voltage)
        return status

    def monitor_loop(self, interval_s: float = 10.0) -> None:
        while not self._shutdown_initiated:
            self.check_once()
            time.sleep(interval_s)

    def _initiate_shutdown(self, voltage: float) -> None:
        self._shutdown_initiated = True
        self.logger.error("Critical battery %.2fV - stopping motors and shutting down", voltage)
        self.movement.stop()
        if self.simulate:
            self.logger.info("[SIM] Shutdown skipped")
            return
        try:
            os.system("sudo shutdown -h now")
        except Exception as exc:  # pragma: no cover - depends on platform
            self.logger.error("Failed to request shutdown: %s", exc)

    def cancel(self) -> None:
        self._shutdown_initiated = True
