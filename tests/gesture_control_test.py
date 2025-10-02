import unittest

from src.gesture_control import DEFAULT_GESTURES, GestureController


class TestGestureController(unittest.TestCase):

    def test_simulation_perform(self):
        controller = GestureController(simulate=True)
        for gesture in DEFAULT_GESTURES:
            controller.perform(gesture)
        controller.perform('unknown')  # should default to rest
        controller.set_positions(0.5, -0.5)
        self.assertEqual(controller.positions, (0.5, -0.5))
        controller.adjust(-0.2, 0.3)
        left, right = controller.positions
        self.assertAlmostEqual(left, 0.3, places=3)
        self.assertAlmostEqual(right, -0.2, places=3)
        controller.close()


if __name__ == '__main__':
    unittest.main()
