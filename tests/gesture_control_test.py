import unittest

from src.gesture_control import DEFAULT_GESTURES, GestureController


class TestGestureController(unittest.TestCase):

    def test_simulation_perform(self):
        controller = GestureController(simulate=True)
        for gesture in DEFAULT_GESTURES:
            controller.perform(gesture)
        controller.perform('unknown')  # should default to rest
        controller.close()


if __name__ == '__main__':
    unittest.main()
