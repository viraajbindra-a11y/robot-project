import unittest

from src.battery_check import BatteryMonitor, BatteryConfig


class TestBatteryMonitor(unittest.TestCase):

    def test_ema_and_classification(self):
        readings = [12.6, 12.5, 12.0, 11.2, 10.7]
        monitor = BatteryMonitor(lambda: readings.pop(0), config=BatteryConfig(smoothing=1.0))
        self.assertEqual(monitor.classify(), 'ok')
        self.assertEqual(monitor.classify(), 'ok')
        self.assertEqual(monitor.classify(), 'ok')
        self.assertEqual(monitor.classify(), 'low')
        self.assertEqual(monitor.classify(), 'critical')

    def test_custom_threshold(self):
        readings = [7.4]
        config = BatteryConfig(critical_voltage=7.2, warn_voltage=7.5)
        monitor = BatteryMonitor(lambda: readings[0], config=config)
        self.assertEqual(monitor.classify(), 'low')


if __name__ == '__main__':
    unittest.main()
