import unittest

from src.battery_check import BatteryMonitor, BatteryConfig
from src.safe_shutdown import SafeShutdown


class TestSafeShutdown(unittest.TestCase):

    def test_shutdown_triggers_at_critical(self):
        readings = [10.5]
        monitor = BatteryMonitor(lambda: readings[0], config=BatteryConfig(critical_voltage=11.0, warn_voltage=11.5))
        handler = SafeShutdown(monitor, simulate=True)
        status = handler.check_once()
        self.assertEqual(status, 'critical')

    def test_warn_state(self):
        readings = [11.2]
        monitor = BatteryMonitor(lambda: readings[0], config=BatteryConfig(critical_voltage=10.0, warn_voltage=11.5))
        handler = SafeShutdown(monitor, simulate=True)
        status = handler.check_once()
        self.assertEqual(status, 'low')


if __name__ == '__main__':
    unittest.main()
