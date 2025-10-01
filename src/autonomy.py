"""Basic obstacle-avoidance autonomy loop.

Moves forward until an obstacle is detected closer than a threshold,
then stops, turns right briefly, and resumes.

Works with real hardware (gpiozero) or in simulation mode.
"""

import argparse
import sys
import time
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.movement import Movement
from src.sensors import UltrasonicSensor


def main(speed: float, threshold_cm: float, turn_time: float, simulate: bool, echo: int, trigger: int, poll: float):
    m = Movement(simulate=simulate)
    s = UltrasonicSensor(echo=echo if not simulate else None,
                         trigger=trigger if not simulate else None,
                         simulate=simulate)
    mode = "HARDWARE" if getattr(m, '_hw', False) else "SIMULATION"
    print(f"Autonomy start ({mode}) speed={speed} threshold={threshold_cm}cm")
    try:
        while True:
            d = s.read_distance_cm()
            status = f"distance={d:.1f}cm" if d is not None else "distance=unknown"
            if d is not None and d < threshold_cm:
                print(f"[AUTO] Obstacle close ({status}) -> stop & turn")
                m.stop()
                # turn away a bit
                m.turn_right(speed)
                time.sleep(turn_time)
                m.stop()
            else:
                m.move_forward(speed)
            if not getattr(m, '_hw', False):
                print(f"[SIM] pos={m.position} dir={m.direction} {status}")
            time.sleep(poll)
    except KeyboardInterrupt:
        print("\nAutonomy stopped by user")
    finally:
        m.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Basic obstacle-avoidance autonomy')
    parser.add_argument('--speed', type=float, default=0.6)
    parser.add_argument('--threshold-cm', type=float, default=25.0)
    parser.add_argument('--turn-time', type=float, default=0.5)
    parser.add_argument('--simulate', action='store_true')
    parser.add_argument('--echo', type=int, default=24, help='BCM pin for echo (hardware only)')
    parser.add_argument('--trigger', type=int, default=25, help='BCM pin for trigger (hardware only)')
    parser.add_argument('--poll', type=float, default=0.15, help='loop sleep seconds')
    args = parser.parse_args()
    main(args.speed, args.threshold_cm, args.turn_time, args.simulate, args.echo, args.trigger, args.poll)
