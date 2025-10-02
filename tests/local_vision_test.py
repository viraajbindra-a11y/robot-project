import unittest


class TestLocalYoloClient(unittest.TestCase):

    def test_missing_dependencies_raise(self):
        try:
            import ultralytics  # noqa: F401
            import cv2  # noqa: F401
            self.skipTest('ultralytics and opencv installed; runtime tested elsewhere')
        except Exception:
            from src.local_vision import LocalYoloClient
            with self.assertRaises(RuntimeError):
                LocalYoloClient()


if __name__ == '__main__':
    unittest.main()
