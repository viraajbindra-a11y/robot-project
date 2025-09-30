"""Movement controller for the robot.

This module provides a Movement class that talks to two motors (left/right).
It prefers gpiozero.Motor when available (recommended on Raspberry Pi). If
gpiozero is not installed or you're running on your development machine,
the methods will fall back to a small simulation so you can test without hardware.

Configure the GPIO pins when creating the Movement object. Defaults are
reasonable examples, but you must set them to match your wiring.
"""

try:
    from gpiozero import Motor  # type: ignore[reportMissingImports]
except Exception:
    Motor = None


def _dir_to_delta(direction):
    """Convert cardinal direction to (dx, dy)."""
    return {
        'N': (0, 1),
        'E': (1, 0),
        'S': (0, -1),
        'W': (-1, 0),
    }[direction]


def _rotate_left(direction):
    order = ['N', 'W', 'S', 'E']
    return order[(order.index(direction) + 1) % 4]


def _rotate_right(direction):
    order = ['N', 'E', 'S', 'W']
    return order[(order.index(direction) + 1) % 4]


class Movement:
    def __init__(self, left_pins=(17, 18), right_pins=(22, 23), simulate: bool = False):
        """Create a Movement controller.

        left_pins/right_pins: tuples (forward_pin, backward_pin) for each motor.
        These are BCM GPIO numbers. Adjust to match your wiring.
        """
        self.left_pins = left_pins
        self.right_pins = right_pins

        # Simulation state (used when hardware not present)
        # position is an (x, y) coordinate on a simple grid
        self.position = [0, 0]
        # direction is one of 'N', 'E', 'S', 'W'
        self.direction = 'N'

        # If simulate=True, force software simulation even if gpiozero is present.
        if Motor and not simulate:
            # gpiozero Motor(forward, backward)
            self.left = Motor(forward=left_pins[0], backward=left_pins[1])
            self.right = Motor(forward=right_pins[0], backward=right_pins[1])
            self._hw = True
        else:
            self.left = None
            self.right = None
            self._hw = False

    def move_forward(self, speed=1.0):
        """Move forward. Speed between 0 (stop) and 1 (full)."""
        if self._hw:
            self.left.forward(speed)
            self.right.forward(speed)
        else:
            # simple grid step: move one unit in current direction
            dx, dy = _dir_to_delta(self.direction)
            self.position[0] += dx
            self.position[1] += dy
            print(f"[SIM] move_forward speed={speed} -> position={self.position}")

    def move_backward(self, speed=1.0):
        """Move backward."""
        if self._hw:
            self.left.backward(speed)
            self.right.backward(speed)
        else:
            dx, dy = _dir_to_delta(self.direction)
            self.position[0] -= dx
            self.position[1] -= dy
            print(f"[SIM] move_backward speed={speed} -> position={self.position}")

    def turn_left(self, speed=1.0):
        """Turn left in place: left motor backward, right motor forward."""
        if self._hw:
            self.left.backward(speed)
            self.right.forward(speed)
        else:
            # rotate direction left (N->W->S->E->N)
            self.direction = _rotate_left(self.direction)
            print(f"[SIM] turn_left speed={speed} -> direction={self.direction}")

    def turn_right(self, speed=1.0):
        """Turn right in place: left forward, right backward."""
        if self._hw:
            self.left.forward(speed)
            self.right.backward(speed)
        else:
            # rotate direction right (N->E->S->W->N)
            self.direction = _rotate_right(self.direction)
            print(f"[SIM] turn_right speed={speed} -> direction={self.direction}")

    def stop(self):
        """Stop both motors."""
        if self._hw:
            self.left.stop()
            self.right.stop()
        else:
            print("[SIM] stop")
