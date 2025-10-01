import unittest

from src.pwm_control import PWMControl


class TestPWMControl(unittest.TestCase):

    def setUp(self):
        self.controller = PWMControl(simulate=True)

    def test_initial_speeds_zero(self):
        self.assertEqual(self.controller.speeds, (0.0, 0.0))

    def test_set_speed_clamps_and_records(self):
        self.controller.set_speed(1.5, -1.5)
        self.assertEqual(self.controller.speeds, (1.0, -1.0))

    def test_brake_stops_both_sides(self):
        self.controller.set_speed(0.5, 0.5)
        self.controller.brake()
        self.assertEqual(self.controller.speeds, (0.0, 0.0))

    def test_stop_zeroes_speed(self):
        self.controller.set_speed(0.3, -0.3)
        self.controller.stop()
        self.assertEqual(self.controller.speeds, (0.0, 0.0))


if __name__ == '__main__':
    unittest.main()
