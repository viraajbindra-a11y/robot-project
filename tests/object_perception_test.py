import unittest

from src.object_perception import ObjectObservation, ObjectRecognizer


class TestObjectPerception(unittest.TestCase):

    def test_simulated_plan(self):
        recognizer = ObjectRecognizer(simulate=True)
        plan = recognizer.plan_grab('red_cube')
        # Simulation can fail to find, but when speech action returned we still get list.
        self.assertIsInstance(plan, list)
        recognizer.close()

    def test_observation_description(self):
        obs = ObjectObservation(
            label='blue_cube',
            color='blue',
            shape='cube',
            distance_cm=32.5,
            angle_deg=18.0,
        )
        description = obs.description()
        self.assertIn('blue', description)
        self.assertIn('cube', description)
        self.assertIn('right', description)

        data = obs.as_dict()
        self.assertEqual(data['color'], 'blue')
        self.assertEqual(data['shape'], 'cube')
        self.assertEqual(data['direction'], 'to your right')

    def test_resolve_and_describe_specific_object(self):
        recognizer = ObjectRecognizer(simulate=True)
        label = recognizer.resolve_label('orange mug')
        self.assertEqual(label, 'orange_mug')
        message = recognizer.describe('orange mug')
        # In simulation the object may or may not appear; ensure string returned.
        self.assertIsInstance(message, str)
        recognizer.close()


if __name__ == '__main__':
    unittest.main()
