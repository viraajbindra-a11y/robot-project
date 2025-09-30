import unittest
from src.voice import Voice


class TestVoice(unittest.TestCase):

    def setUp(self):
        self.voice = Voice()

    def test_speak(self):
        response = self.voice.speak("Hello, Robot!")
        self.assertEqual(response, "Speaking: Hello, Robot!")

    def test_listen(self):
        self.voice.listen("What is your name?")
        self.assertEqual(self.voice.last_command, "What is your name?")


if __name__ == '__main__':
    unittest.main()