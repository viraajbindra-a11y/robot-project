"""Battery monitoring helpers."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional

LOGGER = logging.getLogger(__name__)

VoltageReader = Callable[[], float]


@dataclass
class BatteryConfig:
    critical_voltage: float = 10.8  # for 3S LiPo (~3.6V per cell)
    warn_voltage: float = 11.4
    sample_interval_s: float = 5.0
    smoothing: float = 0.6  # exponential moving average factor


class BatteryMonitor:
    def __init__(self, reader: VoltageReader, *, config: BatteryConfig = BatteryConfig(), logger: Optional[logging.Logger] = None) -> None:
        self.reader = reader
        self.config = config
        self.logger = logger or LOGGER
        self._ema: Optional[float] = None
        self._running = False

    @property
    def voltage(self) -> Optional[float]:
        return self._ema

    def sample(self) -> float:
        reading = self.reader()
        if reading <= 0:
            self.logger.warning("Battery monitor returned %.2fV", reading)
        if self._ema is None:
            self._ema = reading
        else:
            alpha = max(0.0, min(1.0, self.config.smoothing))
            self._ema = alpha * reading + (1 - alpha) * self._ema
        self.logger.debug("Battery reading=%.2fV ema=%.2fV", reading, self._ema)
        return self._ema

    def classify(self) -> str:
        voltage = self.sample()
        if voltage <= self.config.critical_voltage:
            return "critical"
        if voltage <= self.config.warn_voltage:
            return "low"
        return "ok"

    def watch(self, callback: Callable[[str, float], None]) -> None:
        self._running = True
        try:
            while self._running:
                voltage = self.sample()
                status = self.classify()
                callback(status, voltage)
                time.sleep(self.config.sample_interval_s)
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
