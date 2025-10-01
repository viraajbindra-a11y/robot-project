import unittest

from src.voice import Voice


class FakeRecognizer:

    def __init__(self):
        self.adjust_calls = []
        self.listen_calls = []

    def adjust_for_ambient_noise(self, source, duration):
        self.adjust_calls.append((source, duration))

    def listen(self, source, timeout=None, phrase_time_limit=None):
        self.listen_calls.append((source, timeout, phrase_time_limit))
        return "audio"

    def recognize_google(self, audio, language=None):
        return f"google:{language}:{audio}"


class FakeMicrophone:

    def __enter__(self):
        return "source"

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeVoice:

    def __init__(self, voice_id, name, languages):
        self.id = voice_id
        self.name = name
        self.languages = languages


class FakeEngine:

    def __init__(self):
        self.props = {'rate': None, 'volume': None, 'voice': None}
        self.voices = [
            FakeVoice('walle_voice', 'Pixar WALL-E', ['en_US']),
            FakeVoice('english_voice', 'English US', ['en_US']),
        ]
        self.say_calls = []

    def setProperty(self, name, value):
        self.props[name] = value

    def getProperty(self, name):
        if name == 'voices':
            return self.voices
        return self.props.get(name)

    def say(self, message):
        self.say_calls.append(message)

    def runAndWait(self):
        self.say_calls.append('run')


class TestVoice(unittest.TestCase):

    def setUp(self):
        self.voice = Voice(simulate=True)

    def test_speak_returns_rendered_message(self):
        response = self.voice.speak("Hello, Robot!")
        self.assertEqual(response, "Speaking: Hello, Robot!")

    def test_listen_records_explicit_command(self):
        self.voice.listen("What is your name?")
        self.assertEqual(self.voice.last_command, "What is your name?")

    def test_listen_without_input_in_simulation(self):
        result = self.voice.listen()
        self.assertIsNone(result)
        self.assertIsNone(self.voice.last_command)

    def test_is_simulation_property(self):
        self.assertTrue(self.voice.is_simulation)

    def test_real_tts_engine_uses_walle_voice(self):
        engine = FakeEngine()
        recognizer = FakeRecognizer()
        mic = FakeMicrophone()

        voice = Voice(
            simulate=False,
            recognizer=recognizer,
            microphone=mic,
            tts_engine=engine,
            voice_keyword='wall',
            speech_rate=120,
            speech_volume=0.7,
        )

        self.assertTrue(voice.output_available)
        self.assertEqual(engine.props['voice'], 'walle_voice')
        self.assertEqual(engine.props['rate'], 120)
        self.assertEqual(engine.props['volume'], 0.7)

        result = voice.speak("Directive?")
        self.assertEqual(result, "Speaking: Directive?")
        self.assertIn("Directive?", engine.say_calls)

    def test_listen_with_fake_recognizer(self):
        engine = FakeEngine()
        recognizer = FakeRecognizer()
        mic = FakeMicrophone()

        voice = Voice(
            simulate=False,
            recognizer=recognizer,
            microphone=mic,
            tts_engine=engine,
            auto_calibrate=False,
        )

        result = voice.listen(timeout=1.5, phrase_time_limit=2.5)
        self.assertEqual(result, "google:en-US:audio")
        self.assertEqual(voice.last_command, "google:en-US:audio")
        self.assertEqual(len(recognizer.listen_calls), 1)

    def test_set_voice_profile_applies_changes(self):
        engine = FakeEngine()
        recognizer = FakeRecognizer()
        mic = FakeMicrophone()

        voice = Voice(
            simulate=False,
            recognizer=recognizer,
            microphone=mic,
            tts_engine=engine,
        )

        voice.set_voice_profile(voice_keyword='robot', speech_rate=90, speech_volume=0.5)
        self.assertEqual(engine.props['rate'], 90)
        self.assertEqual(engine.props['volume'], 0.5)



if __name__ == '__main__':
    unittest.main()
