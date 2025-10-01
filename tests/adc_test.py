import os
import unittest

from src.utils.adc import ADS1115Config, create_voltage_reader


class TestADCFactory(unittest.TestCase):

    def test_env_reader_default(self):
        reader = create_voltage_reader('env', env_var='TEST_BATTERY_VAR', env_default=13.3)
        self.assertEqual(reader(), 13.3)
        os.environ['TEST_BATTERY_VAR'] = '15.1'
        try:
            self.assertAlmostEqual(reader(), 15.1)
        finally:
            os.environ.pop('TEST_BATTERY_VAR', None)

    def test_ads_falls_back_without_hardware(self):
        reader = create_voltage_reader('ads1115', env_var='TEST_BATTERY_VAR', env_default=11.0, ads_config=ADS1115Config())
        self.assertEqual(reader(), 11.0)

    def test_invalid_driver(self):
        with self.assertRaises(ValueError):
            create_voltage_reader('unknown')


if __name__ == '__main__':
    unittest.main()
