"""Helpers for reading battery voltage via optional ADC hardware."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Optional

import logging

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - optional hardware dependency
    import board  # type: ignore
    import busio  # type: ignore
    from adafruit_ads1x15.analog_in import AnalogIn  # type: ignore
    from adafruit_ads1x15.ads1115 import ADS1115, ADS  # type: ignore
except Exception:  # pragma: no cover - fall back when unavailable
    board = None  # type: ignore
    busio = None  # type: ignore
    AnalogIn = None  # type: ignore
    ADS1115 = None  # type: ignore
    ADS = None  # type: ignore


class ADCUnavailableError(RuntimeError):
    """Raised when the requested ADC backend is unavailable."""


@dataclass
class ADS1115Config:
    address: int = 0x48
    channel: int = 0
    gain: int = 1
    voltage_divider_ratio: float = 2.0  # e.g. 2:1 divider doubles measured voltage


def _build_ads_channel(config: ADS1115Config) -> Callable[[], float]:  # pragma: no cover - requires hardware
    if None in (board, busio, AnalogIn, ADS1115, ADS):
        raise ADCUnavailableError("ADS1115 dependencies not available")
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS1115(i2c, address=config.address, gain=config.gain)
    channels = [ADS.P0, ADS.P1, ADS.P2, ADS.P3]
    try:
        channel = channels[config.channel]
    except IndexError as exc:
        raise ValueError(f"Invalid ADS1115 channel index: {config.channel}") from exc
    analog_in = AnalogIn(ads, channel)

    def reader() -> float:
        return analog_in.voltage * config.voltage_divider_ratio

    return reader


def create_voltage_reader(
    driver: str = "env",
    *,
    env_var: str = "ROBOT_BATTERY_VOLTS",
    env_default: float = 12.0,
    ads_config: Optional[ADS1115Config] = None,
) -> Callable[[], float]:
    """Return a callable that reads the battery voltage.

    ``driver`` can be ``env`` (default) or ``ads1115``.
    """

    driver = driver.lower()
    if driver == "env":
        def reader() -> float:
            value = os.environ.get(env_var)
            return float(value) if value is not None else float(env_default)
        return reader

    if driver == "ads1115":
        config = ads_config or ADS1115Config()
        try:
            return _build_ads_channel(config)
        except ADCUnavailableError as exc:  # pragma: no cover - when hardware missing
            LOGGER.warning("ADS1115 unavailable (%s); falling back to env reader", exc)
            return create_voltage_reader("env", env_var=env_var, env_default=env_default)

    raise ValueError(f"Unknown battery reader driver: {driver}")
