import unittest

from src.chatbot import Chatbot


class TestChatbotFallback(unittest.TestCase):
    def test_generate_reply_friendly(self):
        bot = Chatbot(attitude='friendly', simulate=True)
        reply = bot.generate_reply('hello there')
        self.assertIsInstance(reply, str)
        self.assertIn('I heard:', reply)


if __name__ == '__main__':
    unittest.main()

