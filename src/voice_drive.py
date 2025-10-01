"""Voice commanded driving."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.movement import Movement
from src.voice import Voice

COMMANDS = {
    'forward': 'forward',
    'move forward': 'forward',
    'backward': 'backward',
    'move backward': 'backward',
    'left': 'left',
    'turn left': 'left',
    'right': 'right',
    'turn right': 'right',
    'stop': 'stop',
}


def run_loop(simulate: bool = False) -> None:
    logging.basicConfig(level=logging.INFO)
    movement = Movement(simulate=simulate)
    voice = Voice(simulate=simulate)
    logging.info("Voice control ready. Say 'forward', 'backward', 'left', 'right', or 'stop'. CTRL+C to quit.")
    try:
        while True:
            phrase = voice.listen(timeout=5.0, phrase_time_limit=5.0)
            if not phrase:
                continue
            cmd = COMMANDS.get(phrase.lower())
            if not cmd:
                voice.speak("Command not recognized")
                continue
            if cmd == 'forward':
                movement.move_forward()
            elif cmd == 'backward':
                movement.move_backward()
            elif cmd == 'left':
                movement.turn_left()
            elif cmd == 'right':
                movement.turn_right()
            elif cmd == 'stop':
                movement.stop()
            voice.speak(f"Executing {cmd}")
    except KeyboardInterrupt:
        logging.info("Stopping voice drive")
    finally:
        movement.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description='Drive robot with voice commands')
    parser.add_argument('--simulate', action='store_true')
    args = parser.parse_args()
    run_loop(simulate=args.simulate)


if __name__ == '__main__':
    main()
