"""Quick smoke test for text-to-speech output."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.voice import Voice


def main() -> None:
    parser = argparse.ArgumentParser(description="Speak supplied sentences through the robot voice stack")
    parser.add_argument('text', nargs='*', help='Text to speak; defaults to a demo line')
    parser.add_argument('--simulate', action='store_true', help='Force simulation even if TTS is available')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    voice = Voice(simulate=args.simulate)
    if args.text:
        message = ' '.join(args.text)
    else:
        message = "Directive? The WALL-E voice test is online."
    result = voice.speak(message)
    print(result)


if __name__ == '__main__':
    main()
