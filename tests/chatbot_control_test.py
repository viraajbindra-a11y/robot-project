import os
import unittest

from src.chatbot import Chatbot


class TestChatbotControl(unittest.TestCase):

    def setUp(self):
        os.environ.pop('OPENAI_API_KEY', None)
        self.bot = Chatbot(attitude='friendly', simulate=True, control_mode=True)

    def test_forward_command(self):
        result = self.bot.generate_control_reply('Please move forward for me')
        actions = result['actions']
        self.assertTrue(any(a['type'] == 'movement' and a['value'] == 'forward' for a in actions))
        self.assertTrue(result['speech'])

    def test_autonomy_toggle(self):
        result = self.bot.generate_control_reply('Can you start autonomy mode?')
        self.assertTrue(any(a['type'] == 'autonomy' and a['value'] == 'start' for a in result['actions']))
        result = self.bot.generate_control_reply('Stop autonomy now')
        self.assertTrue(any(a['type'] == 'autonomy' and a['value'] == 'stop' for a in result['actions']))

    def test_gesture_detection(self):
        result = self.bot.generate_control_reply('Wave to the humans!')
        self.assertTrue(any(a['type'] == 'gesture' and a['value'] == 'wave' for a in result['actions']))

    def test_gripper_detection(self):
        result = self.bot.generate_control_reply('Grab that cube!')
        self.assertTrue(any(a['type'] == 'gripper' and a['value'] == 'close' for a in result['actions']))
        self.assertTrue(any(a['type'] == 'task' and a['value'].startswith('grab:') for a in result['actions']))
        result = self.bot.generate_control_reply('Release the cube now')
        self.assertTrue(any(a['type'] == 'gripper' and a['value'] == 'open' for a in result['actions']))

    def test_vision_describe_all(self):
        result = self.bot.generate_control_reply('What do you see around you?')
        self.assertTrue(any(a['type'] == 'vision' and a['value'].startswith('describe') for a in result['actions']))

    def test_vision_describe_specific(self):
        result = self.bot.generate_control_reply('Do you see the orange mug?')
        self.assertTrue(any(a['type'] == 'vision' and a['value'] == 'describe:orange_mug' for a in result['actions']))


if __name__ == '__main__':
    unittest.main()
