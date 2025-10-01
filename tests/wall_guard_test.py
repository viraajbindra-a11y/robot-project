import unittest

from src.wall_guard import WallGuard


class FakeSensor:
    def __init__(self, readings):
        self._readings = readings
        self._index = 0

    @property
    def distance_cm(self):  # type: ignore[override]
        if self._index < len(self._readings):
            value = self._readings[self._index]
            self._index += 1
            return value
        return self._readings[-1]

    def close(self):
        pass


class TestWallGuard(unittest.TestCase):

    def test_hysteresis(self):
        sensor = FakeSensor([30, 18, 22, 27])
        guard = WallGuard(sensor, stop_threshold_cm=20, resume_threshold_cm=25)
        self.assertTrue(guard.allows_forward())  # 30 -> clear
        self.assertFalse(guard.allows_forward())  # 18 -> blocked
        self.assertFalse(guard.allows_forward())  # 22 -> still blocked (within hysteresis)
        self.assertTrue(guard.allows_forward())   # 27 -> resume
        guard.close()


if __name__ == '__main__':
    unittest.main()
