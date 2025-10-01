import unittest
from pathlib import Path

from src.personality_adapter import PersonalityAdapter, DEFAULT_PERSONA, load_persona_from_file


class TestPersonalityAdapter(unittest.TestCase):

    def test_apply_uses_persona(self):
        adapter = PersonalityAdapter({**DEFAULT_PERSONA, 'tone': 'excited', 'catchphrase': 'Yay!'})
        self.assertIn('Yay', adapter.apply('We did it'))

    def test_hook_runs(self):
        def hook(msg, persona):
            return msg + ' beep'

        adapter = PersonalityAdapter(DEFAULT_PERSONA, response_hook=hook)
        self.assertTrue(adapter.apply('Running').endswith('beep'))

    def test_load_persona_file(self):
        tmp = Path('tests/tmp_persona.txt')
        tmp.write_text('tone=excited\n', encoding='utf-8')
        persona = load_persona_from_file(str(tmp))
        self.assertEqual(persona['tone'], 'excited')
        tmp.unlink()


if __name__ == '__main__':
    unittest.main()
