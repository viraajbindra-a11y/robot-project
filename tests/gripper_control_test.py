import unittest

from src.gripper_control import GripperController


class TestGripperController(unittest.TestCase):

    def test_simulated_open_close(self):
        controller = GripperController(pin=None, simulate=True)
        controller.close()
        controller.open()
        controller.toggle()
        controller.toggle()
        controller.close_controller()


if __name__ == '__main__':
    unittest.main()
