"""Simple keyboard teleop without curses.

Reads single keypresses from stdin using termios/tty. Works on POSIX
terminals. Controls: W/A/S/D (case-insensitive) or arrow keys, space=stop, q=quit.

Usage:
    python3 src/keyboard_control_simple.py [--speed 0.8] [--simulate]
"""

import argparse
import sys
import termios
import tty
import select
import time
from src.movement import Movement


ARROW_PREFIX = '\x1b['


def read_key(timeout=0.1):
    """Read a single key (non-blocking up to timeout seconds).
    Returns the string read (possibly multi-byte for arrows), or None if nothing.
    """
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        rlist, _, _ = select.select([fd], [], [], timeout)
        if not rlist:
            return None
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            # possibly an arrow key sequence
            rest = sys.stdin.read(2)
            return ch + rest
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main(speed=0.8, simulate=False):
    m = Movement(simulate=simulate)
    print(f"Starting simple teleop (mode: {'HARDWARE' if getattr(m, '_hw', False) else 'SIMULATION'})")
    print("Controls: W/A/S/D or arrows, space=stop, q=quit")

    try:
        while True:
            key = read_key(timeout=0.2)
            if key is None:
                # idle
                time.sleep(0.01)
                continue
            # normalize
            if key in ('w', 'W', '\x1b[A'):
                m.move_forward(speed)
            elif key in ('s', 'S', '\x1b[B'):
                m.move_backward(speed)
            elif key in ('a', 'A', '\x1b[D'):
                m.turn_left(speed)
            elif key in ('d', 'D', '\x1b[C'):
                m.turn_right(speed)
            elif key == ' ':
                m.stop()
            elif key in ('q', 'Q'):
                m.stop()
                print('Quitting teleop')
                break
            # echo status in simulation mode
            if not getattr(m, '_hw', False):
                print(f"pos={m.position} dir={m.direction}")
    except KeyboardInterrupt:
        m.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--speed', type=float, default=0.8)
    parser.add_argument('--simulate', action='store_true')
    args = parser.parse_args()
    main(speed=args.speed, simulate=args.simulate)
