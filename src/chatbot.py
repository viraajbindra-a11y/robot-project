"""Chatbot bridge: STT -> Chat model -> TTS

Features:
- Uses VOSK for speech-to-text when available, otherwise falls back to stdin input.
- Uses OpenAI (if installed and OPENAI_API_KEY set) to generate responses; otherwise uses a simple rule-based fallback.
- Uses pyttsx3 for text-to-speech when available, otherwise prints the response.
- Accepts an `--attitude` argument to steer the personality of the replies.

This is intentionally lightweight so it works for offline development and on a Pi.
"""

import argparse
import os
import sys
import json
import time

try:
    import openai  # type: ignore[reportMissingImports]
    # Detect new-style client (openai>=1.0) if available
    from openai import OpenAI as _OpenAIClient  # type: ignore[reportMissingImports]
    _HAS_OPENAI = True
    _HAS_OPENAI_V1 = True
except Exception:
    try:
        import openai  # type: ignore[reportMissingImports]
        _OpenAIClient = None  # type: ignore
        _HAS_OPENAI = True
        _HAS_OPENAI_V1 = False
    except Exception:
        _HAS_OPENAI = False
        _HAS_OPENAI_V1 = False

try:
    import pyttsx3  # type: ignore[reportMissingImports]
    _HAS_PYTTSX3 = True
except Exception:
    _HAS_PYTTSX3 = False

try:
    from vosk import Model, KaldiRecognizer  # type: ignore[reportMissingImports]
    import sounddevice as sd  # type: ignore[reportMissingImports]
    _HAS_VOSK = True
except Exception:
    _HAS_VOSK = False


class Chatbot:
    def __init__(self, attitude='friendly', simulate=False):
        self.attitude = attitude
        self.simulate = simulate
        self.tts_engine = None
        if _HAS_PYTTSX3 and not simulate:
            try:
                self.tts_engine = pyttsx3.init()
            except Exception:
                self.tts_engine = None

    def speak(self, text):
        if self.tts_engine:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        else:
            print("[TTS]", text)

    def generate_reply(self, user_text):
        prompt = self._build_prompt(user_text)
        # Try OpenAI if available and API key present
        if _HAS_OPENAI and os.environ.get('OPENAI_API_KEY'):
            try:
                if _HAS_OPENAI_V1 and _OpenAIClient is not None:
                    client = _OpenAIClient()
                    resp = client.chat.completions.create(
                        model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
                        messages=[{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_text}],
                        max_tokens=200,
                    )
                    return resp.choices[0].message.content.strip()
                else:
                    # Legacy API (openai<1.0)
                    openai.api_key = os.environ.get('OPENAI_API_KEY')
                    resp = openai.ChatCompletion.create(
                        model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
                        messages=[{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_text}],
                        max_tokens=200,
                    )
                    return resp.choices[0].message.content.strip()
            except Exception as e:
                print("OpenAI call failed, falling back:", e)

        # Local fallback: echo with attitude
        if self.attitude == 'grumpy':
            return f"Ugh. You said: {user_text}. Figure it out yourself."
        if self.attitude == 'cheerful':
            return f"Sure! You said: {user_text}. That's awesome! Here's an idea..."
        # default friendly
        return f"I heard: {user_text}. How can I help further?"

    def _build_prompt(self, user_text):
        # Build a short system prompt to steer personality
        tone = {
            'friendly': 'You are a friendly helpful robot assistant.' ,
            'grumpy': 'You are a grumpy, curt robot that responds with attitude.',
            'cheerful': 'You are a very cheerful and upbeat robot.'
        }.get(self.attitude, 'You are a friendly helpful robot assistant.')
        return tone

    def listen_stdin(self):
        # Simple stdin-based listen for offline/dev use
        print('Type a message and press Enter (or Ctrl-C to quit):')
        return sys.stdin.readline().strip()

    def listen_vosk(self, model_path='model'):
        if self.simulate:
            return None
        if not _HAS_VOSK:
            raise RuntimeError('vosk not available')
        if not os.path.exists(model_path):
            raise RuntimeError(f'VOSK model not found at {model_path}. Download and extract a model into that path.')

        model = Model(model_path)
        # use default device and settings
        samplerate = 16000
        device_info = sd.query_devices(kind='input')
        if 'default_samplerate' in device_info:
            samplerate = int(device_info['default_samplerate'])

        rec = KaldiRecognizer(model, samplerate)
        print('Listening (press Ctrl-C to stop)')
        def callback(indata, frames, time_info, status):
            if rec.AcceptWaveform(indata.tobytes()):
                res = rec.Result()
                j = json.loads(res)
                text = j.get('text', '')
                if text:
                    print('[STT]', text)

        with sd.RawInputStream(samplerate=samplerate, blocksize=8000, dtype='int16', channels=1, callback=callback):
            while True:
                time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser(description='Chatbot bridge: STT -> Chat -> TTS')
    parser.add_argument('--attitude', default='friendly', choices=['friendly', 'cheerful', 'grumpy'])
    parser.add_argument('--simulate', action='store_true', help="Don't use audio devices; read text from stdin and print TTS")
    parser.add_argument('--vosk-model', default='model', help='Path to VOSK model directory')
    parser.add_argument('--persona-file', default=None, help='Path to a persona file to use as system prompt')
    args = parser.parse_args()

    persona_text = None
    if args.persona_file:
        try:
            with open(args.persona_file, 'r', encoding='utf-8') as f:
                persona_text = f.read()
        except Exception as e:
            print('Failed to read persona file:', e)

    bot = Chatbot(attitude=args.attitude, simulate=args.simulate)

    try:
        while True:
            if _HAS_VOSK and not args.simulate:
                print('VOSK mode not fully interactive in this demo. Falling back to stdin.')
                user = bot.listen_stdin()
            else:
                user = bot.listen_stdin()
            if not user:
                continue
            if user.lower() in ('quit', 'exit'):
                print('Goodbye')
                break

            # If persona text is provided, prefer OpenAI with persona as system prompt
            if persona_text and _HAS_OPENAI and os.environ.get('OPENAI_API_KEY'):
                try:
                    if _HAS_OPENAI_V1 and _OpenAIClient is not None:
                        client = _OpenAIClient()
                        resp = client.chat.completions.create(
                            model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
                            messages=[{'role': 'system', 'content': persona_text}, {'role': 'user', 'content': user}],
                            max_tokens=300,
                        )
                        reply = resp.choices[0].message.content.strip()
                    else:
                        openai.api_key = os.environ.get('OPENAI_API_KEY')
                        resp = openai.ChatCompletion.create(
                            model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
                            messages=[{'role': 'system', 'content': persona_text}, {'role': 'user', 'content': user}],
                            max_tokens=300,
                        )
                        reply = resp.choices[0].message.content.strip()
                except Exception as e:
                    print('OpenAI persona call failed, falling back:', e)
                    reply = bot.generate_reply(user)
            else:
                # For fallback, bias the reply by embedding a short prefix from persona_text if available
                if persona_text:
                    # use first 200 chars as a style hint
                    style_hint = persona_text[:200]
                    reply = f"{style_hint}\n{bot.generate_reply(user)}"
                else:
                    reply = bot.generate_reply(user)

            bot.speak(reply)
    except KeyboardInterrupt:
        print('\nInterrupted')


if __name__ == '__main__':
    main()
