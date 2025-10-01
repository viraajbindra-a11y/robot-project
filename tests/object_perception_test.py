import unittest

from src.object_perception import ObjectRecognizer


class TestObjectPerception(unittest.TestCase):

    def test_simulated_plan(self):
        recognizer = ObjectRecognizer(simulate=True)
        plan = recognizer.plan_grab('red_cube')
        # Simulation can fail to find, but when speech action returned we still get list.
        self.assertIsInstance(plan, list)
        recognizer.close()


if __name__ == '__main__':
    unittest.main()
