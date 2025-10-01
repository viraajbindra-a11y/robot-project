"""Optional future feature: vision-assisted chat."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.camera_vision import CameraVision
from src.personality_adapter import PersonalityAdapter, DEFAULT_PERSONA
from src.voice import Voice


def main() -> None:
    parser = argparse.ArgumentParser(description='Ask the robot what it sees (simulation friendly)')
    parser.add_argument('--simulate', action='store_true')
    parser.add_argument('--device', type=int, default=0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    persona = PersonalityAdapter(DEFAULT_PERSONA)
    voice = Voice(simulate=args.simulate)
    vision = CameraVision(device=args.device, simulate=args.simulate)

    try:
        for idx, frame in enumerate(vision.frames()):
            if idx % 30 != 0:  # respond roughly every 30 frames
                continue
            if frame is None:
                continue
            message = f"I can see {frame.faces} faces right now."
            voice.speak(persona.apply(message))
    except KeyboardInterrupt:
        logging.info('Stopping vision chat')
    finally:
        vision.close()


if __name__ == '__main__':
    main()
