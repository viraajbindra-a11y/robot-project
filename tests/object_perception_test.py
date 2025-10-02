import json
import tempfile
import unittest
from pathlib import Path

from src.object_perception import ObjectObservation, ObjectRecognizer


class FakeRemoteVision:
    def __init__(self, payload):
        self.payload = payload

    def detect(self):
        return self.payload


class TestObjectPerception(unittest.TestCase):

    def test_simulated_plan(self):
        recognizer = ObjectRecognizer(simulate=True)
        plan = recognizer.plan_grab('red_cube')
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
        label = recognizer.resolve_label('coffee mug')
        self.assertEqual(label, 'orange_mug')
        message = recognizer.describe('orange mug')
        self.assertIsInstance(message, str)
        recognizer.close()

    def test_remote_integration(self):
        remote = FakeRemoteVision([
            {'label': 'purple ball', 'distance_cm': 42.0, 'angle_deg': -8.0},
        ])
        recognizer = ObjectRecognizer(simulate=True, remote_client=remote)
        obs = recognizer.observations()
        self.assertTrue(obs)
        self.assertEqual(obs[0].label, 'purple_ball')
        self.assertIn('purple', recognizer.describe('purple ball'))
        recognizer.close()

    def test_load_color_map(self):
        data = {
            'white_cube': {
                'h': [0, 10],
                's': [0, 30],
                'v': [180, 255],
                'color': 'white',
                'shape': 'cube',
                'aliases': ['white block'],
            }
        }
        with tempfile.NamedTemporaryFile('w', delete=False) as handle:
            json.dump(data, handle)
            path = handle.name
        loaded = ObjectRecognizer.load_color_map(path)
        self.assertIn('white_cube', loaded)
        Path(path).unlink(missing_ok=True)

    def test_update_color_map(self):
        recognizer = ObjectRecognizer(simulate=True)
        recognizer.update_color_map({
            'pink_flower': {
                'h': (150, 170),
                's': (120, 255),
                'v': (120, 255),
                'color': 'pink',
                'shape': 'flower',
                'aliases': ['pink blossom'],
            }
        })
        self.assertEqual(recognizer.resolve_label('pink blossom'), 'pink_flower')
        recognizer.close()


if __name__ == '__main__':
    unittest.main()
