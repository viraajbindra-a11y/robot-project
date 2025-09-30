import unittest
from src.movement import Movement


class TestMovement(unittest.TestCase):
    
    def setUp(self):
        # Force simulation to avoid requiring hardware/gpiozero during tests
        self.robot = Movement(simulate=True)

    def test_move_forward(self):
        initial_position = list(self.robot.position)
        self.robot.move_forward()
        self.assertNotEqual(initial_position, self.robot.position)

    def test_move_backward(self):
        initial_position = list(self.robot.position)
        self.robot.move_backward()
        self.assertNotEqual(initial_position, self.robot.position)

    def test_turn_left(self):
        initial_direction = self.robot.direction
        self.robot.turn_left()
        self.assertNotEqual(initial_direction, self.robot.direction)

    def test_turn_right(self):
        initial_direction = self.robot.direction
        self.robot.turn_right()
        self.assertNotEqual(initial_direction, self.robot.direction)


if __name__ == '__main__':
    unittest.main()
