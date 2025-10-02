"""Chatbot bridge: STT -> Chat model -> TTS.

Works both offline (stdin + console TTS) and online (VOSK + OpenAI). It also
supports a structured "control" mode used by the master brain to receive action
instructions alongside dialogue.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

try:
    import openai  # type: ignore[reportMissingImports]
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

LOGGER = logging.getLogger(__name__)

CONTROL_SYSTEM_PROMPT = (
    "You are the control brain for a playful WALL-E style robot."
    " Respond ONLY with JSON using this schema:\n"
    "{\n  \"speech\": \"text the robot should speak\",\n"
    "  \"actions\": [\n    {\"type\": \"movement|autonomy|gesture|gripper|vision|other\", \"value\": \"...\"}\n  ]\n}"
    " Use movement values forward, backward, left, right, stop."
    " Use autonomy values start or stop. For gestures use wave, point, nod, salute, rest."
    " For gripper use open, close, or toggle."
    " Vision values should be describe or describe:<object label>. Keep speech short and in character."
)


class Chatbot:
    def __init__(self, attitude: str = 'friendly', simulate: bool = False, *, control_mode: bool = False):
        self.attitude = attitude
        self.simulate = simulate
        self.control_mode = control_mode
        self.tts_engine = None
        if _HAS_PYTTSX3 and not simulate:
            try:
                self.tts_engine = pyttsx3.init()
            except Exception:
                self.tts_engine = None

    def speak(self, text: str) -> None:
        if self.tts_engine:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        else:
            print("[TTS]", text)

    def generate_reply(self, user_text: str) -> str:
        prompt = self._build_prompt()
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
                    openai.api_key = os.environ.get('OPENAI_API_KEY')
                    resp = openai.ChatCompletion.create(
                        model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
                        messages=[{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_text}],
                        max_tokens=200,
                    )
                    return resp.choices[0].message.content.strip()
            except Exception as exc:
                LOGGER.warning("OpenAI call failed, falling back: %s", exc)

        if self.attitude == 'grumpy':
            return f"Ugh. You said: {user_text}. Figure it out yourself."
        if self.attitude == 'cheerful':
            return f"Sure! You said: {user_text}. That's awesome! Here's an idea..."
        return f"I heard: {user_text}. How can I help further?"

    def generate_control_reply(self, user_text: str, *, persona_text: Optional[str] = None) -> Dict[str, Any]:
        if _HAS_OPENAI and os.environ.get('OPENAI_API_KEY'):
            system_prompt = CONTROL_SYSTEM_PROMPT
            if persona_text:
                system_prompt += f"\nPersona background:\n{persona_text}\n"
            try:
                if _HAS_OPENAI_V1 and _OpenAIClient is not None:
                    client = _OpenAIClient()
                    resp = client.chat.completions.create(
                        model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
                        messages=[
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': user_text},
                        ],
                        max_tokens=250,
                    )
                    reply = resp.choices[0].message.content.strip()
                else:
                    openai.api_key = os.environ.get('OPENAI_API_KEY')
                    resp = openai.ChatCompletion.create(
                        model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
                        messages=[
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': user_text},
                        ],
                        max_tokens=250,
                    )
                    reply = resp.choices[0].message.content.strip()
                parsed = self._parse_control_json(reply)
                if parsed is not None:
                    return parsed
                LOGGER.warning("Control JSON parse failed, reply=%s", reply)
            except Exception as exc:
                LOGGER.warning("OpenAI control call failed, falling back: %s", exc)

        actions = self._infer_actions(user_text)
        if actions:
            speech = self._fallback_speech(actions)
        else:
            speech = self.generate_reply(user_text)
        return {'speech': speech, 'actions': actions}

    def _parse_control_json(self, reply: str) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(reply)
        except Exception:
            return None
        speech = data.get('speech')
        actions = data.get('actions', [])
        if not isinstance(speech, str) or not isinstance(actions, list):
            return None
        normalised: List[Dict[str, str]] = []
        for item in actions:
            if not isinstance(item, dict):
                continue
            typ = item.get('type')
            value = item.get('value')
            if isinstance(typ, str) and isinstance(value, str):
                normalised.append({'type': typ.lower(), 'value': value.lower()})
        return {'speech': speech, 'actions': normalised}

    def _infer_actions(self, user_text: str) -> List[Dict[str, str]]:
        text = user_text.lower()
        actions: List[Dict[str, str]] = []
        if any(word in text for word in ('autonomy', 'auto', 'self drive')):
            if any(word in text for word in ('stop', 'disable', 'off', 'halt')):
                actions.append({'type': 'autonomy', 'value': 'stop'})
            else:
                actions.append({'type': 'autonomy', 'value': 'start'})
        if any(word in text for word in ('forward', 'ahead', 'advance', 'move out')):
            actions.append({'type': 'movement', 'value': 'forward'})
        if any(word in text for word in ('back', 'reverse', 'backward')):
            actions.append({'type': 'movement', 'value': 'backward'})
        if 'left' in text and 'left arm' not in text:
            actions.append({'type': 'movement', 'value': 'left'})
        if 'right' in text and 'right arm' not in text:
            actions.append({'type': 'movement', 'value': 'right'})
        if 'stop' in text and not any(a['value'] == 'stop' for a in actions if a['type'] == 'movement'):
            actions.append({'type': 'movement', 'value': 'stop'})
        if any(word in text for word in ('wave', 'wave your', 'say hi', 'hello there')):
            actions.append({'type': 'gesture', 'value': 'wave'})
        if 'salute' in text:
            actions.append({'type': 'gesture', 'value': 'salute'})
        if any(word in text for word in ('point', 'point at')):
            actions.append({'type': 'gesture', 'value': 'point'})
        if 'nod' in text or 'yes' in text and 'head' in text:
            actions.append({'type': 'gesture', 'value': 'nod'})
        if any(word in text for word in ('rest arms', 'hands down', 'relax arms')):
            actions.append({'type': 'gesture', 'value': 'rest'})
        object_labels = {
            'red cube': 'red_cube',
            'green cube': 'green_cube',
            'blue cube': 'blue_cube',
            'cube': 'red_cube',
            'block': 'red_cube',
            'orange mug': 'orange_mug',
            'orange cup': 'orange_mug',
            'mug': 'orange_mug',
            'coffee mug': 'orange_mug',
            'black box': 'black_box',
            'black cube': 'black_box',
        }
        grab_keywords = ('grab', 'grip', 'clamp', 'hold tight', 'pick up', 'pick it up')
        if any(word in text for word in grab_keywords):
            selected = None
            for phrase, label in object_labels.items():
                if phrase in text:
                    selected = label
                    break
            if selected:
                actions.append({'type': 'task', 'value': f'grab:{selected}'})
            actions.append({'type': 'gripper', 'value': 'close'})
        if any(word in text for word in ('what do you see', 'what can you see', 'describe what you see', 'look around', 'spot anything', 'describe the room', 'anything you see', 'do you see')):
            detail = None
            for phrase, label in object_labels.items():
                if phrase in text:
                    detail = label
                    break
            if detail:
                actions.append({'type': 'vision', 'value': f'describe:{detail}'})
            else:
                actions.append({'type': 'vision', 'value': 'describe'})

        if any(word in text for word in ('show me the', 'where is the', 'do you see the', 'find the')):
            for phrase, label in object_labels.items():
                if phrase in text:
                    actions.append({'type': 'vision', 'value': f'describe:{label}'})
                    break

        if any(word in text for word in ('release', 'drop', 'let go', 'open hand')):
            actions.append({'type': 'gripper', 'value': 'open'})
        if 'toggle gripper' in text or 'toggle claw' in text:
            actions.append({'type': 'gripper', 'value': 'toggle'})

        arm_actions = self._infer_arm_actions(text)
        actions.extend(arm_actions)
        tuning_actions = self._infer_tuning_actions(text)
        actions.extend(tuning_actions)
        return actions

    def _fallback_speech(self, actions: List[Dict[str, str]]) -> str:
        summary = ', '.join(f"{a['type']} {a['value']}" for a in actions)
        if any(a['type'] == 'vision' for a in actions):
            if self.attitude == 'grumpy':
                return 'Fine. I will look.'
            if self.attitude == 'cheerful':
                return 'Scanning the scene!'
            return 'Let me take a look.'
        if any(a['type'] == 'arms' for a in actions):
            if self.attitude == 'grumpy':
                return 'Moving the arms. Don’t make me drop anything.'
            if self.attitude == 'cheerful':
                return 'Arms moving! Flex time!'
            return 'Adjusting the arms.'
        if self.attitude == 'grumpy':
            return f"Fine. {summary}."
        if self.attitude == 'cheerful':
            return f"On it! {summary}!"
        return f"Executing {summary}."

    def _infer_arm_actions(self, text: str) -> List[Dict[str, str]]:
        actions: List[Dict[str, str]] = []
        if 'arm' not in text:
            return actions

        numbers = [float(match.group()) for match in re.finditer(r'-?\d+(?:\.\d+)?', text)]
        clamp = lambda value: max(-1.0, min(1.0, value))

        def build_action(kind: str, left: float, right: float) -> None:
            actions.append({'type': 'arms', 'value': f'{kind}:{left:.3f}:{right:.3f}'})

        if 'set arms' in text or 'set left arm' in text or 'set right arm' in text:
            if 'left' in text and 'right' in text and len(numbers) >= 2:
                build_action('set', clamp(numbers[0]), clamp(numbers[1]))
                return actions
            if 'left' in text and numbers:
                build_action('set_left', clamp(numbers[0]), 0.0)
                return actions
            if 'right' in text and numbers:
                build_action('set_right', 0.0, clamp(numbers[0]))
                return actions
            if len(numbers) >= 2:
                build_action('set', clamp(numbers[0]), clamp(numbers[1]))
                return actions
        if any(phrase in text for phrase in ('raise left arm', 'lift left arm')):
            build_action('adjust', 0.2, 0.0)
        if any(phrase in text for phrase in ('lower left arm', 'drop left arm')):
            build_action('adjust', -0.2, 0.0)
        if any(phrase in text for phrase in ('raise right arm', 'lift right arm')):
            build_action('adjust', 0.0, 0.2)
        if any(phrase in text for phrase in ('lower right arm', 'drop right arm')):
            build_action('adjust', 0.0, -0.2)
        if 'raise both arms' in text or 'arms up' in text:
            build_action('adjust', 0.2, 0.2)
        if 'arms down' in text or 'lower both arms' in text:
            build_action('adjust', -0.2, -0.2)
        return actions

    def _infer_tuning_actions(self, text: str) -> List[Dict[str, str]]:
        actions: List[Dict[str, str]] = []
        if not any(keyword in text for keyword in ('speed', 'trim', 'motor', 'slow', 'fast')):
            return actions

        numbers = [float(match.group()) for match in re.finditer(r'-?\d+(?:\.\d+)?', text)]

        def add(action: str) -> None:
            actions.append({'type': 'tuning', 'value': action})

        first_number = numbers[0] if numbers else None
        if 'set speed' in text and first_number is not None:
            add(f'speed_set:{max(0.0, min(1.5, first_number)):.3f}')
        if any(phrase in text for phrase in ('increase speed', 'speed up', 'go faster')):
            delta = first_number if first_number is not None else 0.1
            add(f'speed_adj:{max(0.01, abs(delta)):.3f}')
        if any(phrase in text for phrase in ('decrease speed', 'slow down', 'go slower')):
            delta = first_number if first_number is not None else 0.1
            add(f'speed_adj:-{max(0.01, abs(delta)):.3f}')

        if 'set left trim' in text and first_number is not None:
            add(f'trim_set:left:{first_number:.3f}')
        if 'set right trim' in text and first_number is not None:
            add(f'trim_set:right:{first_number:.3f}')
        if 'reset trim' in text or 'balance motors' in text:
            add('trim_reset')

        default_delta = first_number if first_number is not None else 0.02
        if 'trim left' in text or 'nudge left motor' in text:
            add(f'trim_adj:left:{default_delta:+.3f}')
        if 'trim right' in text or 'nudge right motor' in text:
            add(f'trim_adj:right:{default_delta:+.3f}')

        return actions

    def _build_prompt(self) -> str:
        return {
            'friendly': 'You are a friendly helpful robot assistant.',
            'grumpy': 'You are a grumpy, curt robot that responds with attitude.',
            'cheerful': 'You are a very cheerful and upbeat robot.',
        }.get(self.attitude, 'You are a friendly helpful robot assistant.')

    def listen_stdin(self) -> str:
        print('Type a message and press Enter (or Ctrl-C to quit):')
        return sys.stdin.readline().strip()

    def listen_vosk(self, model_path: str = 'model') -> None:
        if self.simulate:
            return None
        if not _HAS_VOSK:
            raise RuntimeError('vosk not available')
        if not os.path.exists(model_path):
            raise RuntimeError(f'VOSK model not found at {model_path}')

        model = Model(model_path)
        samplerate = 16000
        device_info = sd.query_devices(kind='input')
        if 'default_samplerate' in device_info:
            samplerate = int(device_info['default_samplerate'])

        rec = KaldiRecognizer(model, samplerate)
        print('Listening (press Ctrl-C to stop)')

        def callback(indata, frames, time_info, status):
            if rec.AcceptWaveform(indata.tobytes()):
                res = rec.Result()
                payload = json.loads(res)
                text = payload.get('text', '')
                if text:
                    print('[STT]', text)

        with sd.RawInputStream(samplerate=samplerate, blocksize=8000, dtype='int16', channels=1, callback=callback):
            while True:
                time.sleep(0.1)


def main() -> None:
    parser = argparse.ArgumentParser(description='Chatbot bridge: STT -> Chat -> TTS')
    parser.add_argument('--attitude', default='friendly', choices=['friendly', 'cheerful', 'grumpy'])
    parser.add_argument('--simulate', action='store_true', help="Use stdin/stdout instead of audio devices")
    parser.add_argument('--vosk-model', default='model', help='Path to VOSK model directory')
    parser.add_argument('--persona-file', default=None, help='Path to a persona file to use as system prompt')
    parser.add_argument('--control', action='store_true', help='Print structured control JSON instead of TTS')
    args = parser.parse_args()

    persona_text = None
    if args.persona_file:
        try:
            with open(args.persona_file, 'r', encoding='utf-8') as handle:
                persona_text = handle.read()
        except Exception as exc:
            print('Failed to read persona file:', exc)

    bot = Chatbot(attitude=args.attitude, simulate=args.simulate, control_mode=args.control)

    try:
        while True:
            if _HAS_VOSK and not args.simulate:
                print('VOSK live capture not fully wired in this CLI demo; using stdin fallback.')
            user = bot.listen_stdin()
            if not user:
                continue
            if user.lower() in ('quit', 'exit'):
                print('Goodbye')
                break

            if args.control:
                payload = bot.generate_control_reply(user, persona_text=persona_text)
                print(json.dumps(payload, indent=2))
            elif persona_text and _HAS_OPENAI and os.environ.get('OPENAI_API_KEY'):
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
                except Exception as exc:
                    print('OpenAI persona call failed, falling back:', exc)
                    reply = bot.generate_reply(user)
                bot.speak(reply)
            else:
                reply = bot.generate_reply(user)
                bot.speak(reply)
    except KeyboardInterrupt:
        print('\nInterrupted')


if __name__ == '__main__':
    main()
