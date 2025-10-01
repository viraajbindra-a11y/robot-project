"""Standalone obstacle avoidance runner."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.auto_drive import AutoDriveConfig, AutoDriver
from src.movement import Movement
from src.sensors import DistanceSensorWrapper


def main() -> None:
    parser = argparse.ArgumentParser(description='Simple obstacle avoidance loop')
    parser.add_argument('--simulate', action='store_true', help='Force simulation even on Pi')
    parser.add_argument('--speed', type=float, default=0.6)
    parser.add_argument('--threshold', type=float, default=25.0, help='Stop distance in cm')
    parser.add_argument('--echo', type=int, help='BCM echo pin for ultrasonic sensor')
    parser.add_argument('--trigger', type=int, help='BCM trigger pin for ultrasonic sensor')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    config = AutoDriveConfig(speed=args.speed, obstacle_threshold_cm=args.threshold)
    movement = Movement(simulate=args.simulate)
    sensor = DistanceSensorWrapper(echo=args.echo, trigger=args.trigger, simulate=args.simulate)
    driver = AutoDriver(config=config, movement=movement, sensor=sensor)
    try:
        driver.run()
    except KeyboardInterrupt:
        logging.info('Stopping obstacle avoidance')
    finally:
        driver.stop()


if __name__ == '__main__':
    main()
