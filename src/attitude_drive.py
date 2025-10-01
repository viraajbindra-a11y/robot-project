"""Tie together personality, movement, and speech."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.movement import Movement
from src.personality_adapter import PersonalityAdapter, DEFAULT_PERSONA, load_persona_from_file
from src.voice import Voice

COMMAND_MOVE_MAP = {
    'forward': 'forward',
    'backward': 'backward',
    'left': 'left',
    'right': 'right',
    'stop': 'stop',
}


def apply_movement(movement: Movement, command: str) -> None:
    if command == 'forward':
        movement.move_forward()
    elif command == 'backward':
        movement.move_backward()
    elif command == 'left':
        movement.turn_left()
    elif command == 'right':
        movement.turn_right()
    elif command == 'stop':
        movement.stop()


def run_loop(voice: Voice, movement: Movement, adapter: PersonalityAdapter) -> None:
    logging.info("Attitude drive ready. Speak commands or type them in simulation mode.")
    try:
        while True:
            command = voice.listen(timeout=5.0, phrase_time_limit=5.0)
            if not command:
                continue
            normalized = command.lower().strip()
            if normalized in ('quit', 'exit'):
                voice.speak(adapter.apply("Signing off"))
                break
            move_cmd = COMMAND_MOVE_MAP.get(normalized)
            if move_cmd:
                apply_movement(movement, move_cmd)
                voice.speak(adapter.apply(f"Directive acknowledged: {move_cmd}"))
            else:
                voice.speak(adapter.apply("Unrecognized directive"))
    except KeyboardInterrupt:
        logging.info("Stopping attitude drive")
    finally:
        movement.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description='Personality-infused driving loop')
    parser.add_argument('--simulate', action='store_true')
    parser.add_argument('--persona', help='Path to persona config')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    persona = DEFAULT_PERSONA
    if args.persona:
        try:
            persona = load_persona_from_file(args.persona)
        except Exception as exc:
            logging.warning("Failed to load persona %s: %s", args.persona, exc)
    adapter = PersonalityAdapter(persona)
    voice = Voice(simulate=args.simulate)
    movement = Movement(simulate=args.simulate)
    run_loop(voice, movement, adapter)


if __name__ == '__main__':
    main()
