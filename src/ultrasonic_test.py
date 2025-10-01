"""CLI to sample the ultrasonic sensor and print readings."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.sensors import DistanceSensorWrapper


def main() -> None:
    parser = argparse.ArgumentParser(description='Read ultrasonic sensor distance repeatedly')
    parser.add_argument('--echo', type=int, help='BCM echo pin')
    parser.add_argument('--trigger', type=int, help='BCM trigger pin')
    parser.add_argument('--simulate', action='store_true', help='Force simulation mode')
    parser.add_argument('--interval', type=float, default=0.2, help='Seconds between reads')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    sensor = DistanceSensorWrapper(echo=args.echo, trigger=args.trigger, simulate=args.simulate)
    try:
        while True:
            distance = sensor.distance_cm
            print(f"Distance: {distance:.1f} cm")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logging.info('Stopping ultrasonic test')
    finally:
        sensor.close()


if __name__ == '__main__':
    main()
