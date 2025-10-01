"""Quick speech-to-text smoke test."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.voice import Voice, VoiceError


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture audio and print transcription")
    parser.add_argument('--simulate', action='store_true', help='Force simulation (no microphone)')
    parser.add_argument('--timeout', type=float, default=5.0, help='Seconds to wait for speech')
    parser.add_argument('--phrase-time-limit', type=float, default=10.0, help='Maximum phrase length in seconds')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    voice = Voice(simulate=args.simulate)
    try:
        text = voice.listen(timeout=args.timeout, phrase_time_limit=args.phrase_time_limit)
        print(f"Transcription: {text}")
    except VoiceError as exc:
        logging.error("Speech collection failed: %s", exc)


if __name__ == '__main__':
    main()
