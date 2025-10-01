import unittest

from src.movement import Movement


class TestMovement(unittest.TestCase):

    def setUp(self):
        # Force simulation to avoid requiring hardware/gpiozero during tests
        self.robot = Movement(simulate=True)

    def test_move_forward_updates_position(self):
        self.robot.move_forward()
        self.assertEqual(self.robot.position, [0.0, 1.0])
        self.assertEqual(self.robot.last_action, ('forward', 1.0))

    def test_move_backward_updates_position(self):
        self.robot.move_backward()
        self.assertEqual(self.robot.position, [0.0, -1.0])
        self.assertEqual(self.robot.last_action, ('backward', 1.0))

    def test_turn_left_updates_direction(self):
        self.robot.turn_left()
        self.assertEqual(self.robot.direction, 'W')
        self.assertEqual(self.robot.last_action, ('turn_left', 1.0))

    def test_turn_right_updates_direction(self):
        self.robot.turn_right()
        self.assertEqual(self.robot.direction, 'E')
        self.assertEqual(self.robot.last_action, ('turn_right', 1.0))

    def test_stop_records_last_action(self):
        self.robot.move_forward(0.3)
        self.robot.stop()
        self.assertEqual(self.robot.last_action, ('stop', 0.0))

    def test_speed_is_clamped(self):
        self.robot.move_forward(2.5)
        self.assertEqual(self.robot.position, [0.0, 1.0])

    def test_negative_speed_raises(self):
        with self.assertRaises(ValueError):
            self.robot.move_forward(-0.1)

    def test_reset_restores_initial_state(self):
        self.robot.move_forward()
        self.robot.turn_right()
        self.robot.reset()
        self.assertEqual(self.robot.position, [0.0, 0.0])
        self.assertEqual(self.robot.direction, 'N')
        self.assertEqual(self.robot.last_action, ('reset', 0.0))


if __name__ == '__main__':
    unittest.main()
