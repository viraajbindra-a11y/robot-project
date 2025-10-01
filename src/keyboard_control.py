"""Keyboard control for the robot.

Run locally for simulation or on the Pi for real motors.
Use arrow keys or WASD to drive. q to quit.
"""

import argparse
import curses
import sys
import time
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.movement import Movement


def main(stdscr, speed, simulate=False):
    # Curses setup
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(100)

    m = Movement(simulate=simulate)

    # show initial mode
    mode = "HARDWARE" if getattr(m, '_hw', False) else "SIMULATION"
    stdscr.clear()
    stdscr.addstr(0, 0, f"Keyboard teleop ({mode}) — W/A/S/D or arrows to drive — space to stop — q to quit")
    stdscr.refresh()

    try:
        while True:
            c = stdscr.getch()
            if c == -1:
                time.sleep(0.01)
                continue
            # WASD or arrow keys
            if c in (ord('w'), curses.KEY_UP):
                m.move_forward(speed)
            elif c in (ord('s'), curses.KEY_DOWN):
                m.move_backward(speed)
            elif c in (ord('a'), curses.KEY_LEFT):
                m.turn_left(speed)
            elif c in (ord('d'), curses.KEY_RIGHT):
                m.turn_right(speed)
            elif c == ord(' '):
                m.stop()
            elif c == ord('q'):
                m.stop()
                break
            # update status (position/direction in simulation)
            stdscr.clear()
            status = f"pos={m.position} dir={m.direction}" if not getattr(m, '_hw', False) else "HARDWARE mode"
            stdscr.addstr(0, 0, f"Keyboard teleop ({mode}) — {status}")
            stdscr.addstr(2, 0, "Controls: W/A/S/D or arrows, space=stop, q=quit")
            stdscr.refresh()
    finally:
        m.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Keyboard teleop for robot')
    parser.add_argument('--speed', type=float, default=0.8, help='movement speed 0-1')
    parser.add_argument('--simulate', action='store_true', help='force simulation mode even if hardware lib present')
    args = parser.parse_args()
    curses.wrapper(main, args.speed, args.simulate)
