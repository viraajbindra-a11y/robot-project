# Robot Project

## Overview
This project is designed to control a robot using movement and voice functionalities. It serves as a foundation
for building more complex robotic applications.

## Project Structure
```
robot-project
├── src
│   ├── robot.py          # Main entry point for the robot application
│   ├── movement.py       # Contains the Movement class for robot control
│   ├── voice.py          # Contains the Voice class for interaction
│   └── utils
│       └── __init__.py   # Initializes the utils package
├── tests
│   ├── movement_test.py   # Unit tests for the Movement class
│   └── voice_test.py      # Unit tests for the Voice class
├── scripts
│   └── sync_to_pi.sh      # Script to synchronize files to Raspberry Pi
├── .gitignore              # Specifies files to ignore in Git
├── requirements.txt        # Lists Python dependencies
└── README.md               # Documentation for the project
```

## Setup Instructions
1. Clone the repository from GitHub:
  ```bash
  git clone <repository-url>
  ```
2. Navigate to the project directory:
  ```bash
  cd robot-project
  ```
3. Install the required dependencies:
  ```bash
  pip install -r requirements.txt
  ```

## Usage
- To run the robot application, execute the following command:
  ```bash
  python src/robot.py
  ```

## Testing
- To run the tests for the Movement class:
  ```bash
  python -m unittest tests/movement_test.py
  ```
- To run the tests for the Voice class:
  ```bash
  python -m unittest tests/voice_test.py
  ```

## Synchronization with Raspberry Pi
- Use the provided script `sync_to_pi.sh` to synchronize your project files with the Raspberry Pi. Make sure to
  configure the script with the correct paths and credentials.

## Contributing
Feel free to fork the repository and submit pull requests for any improvements or features you would like to add.

## Milestone 3 — Locomotion (Wheels & Motor Driver)

Goal: get the robot moving under keyboard control from the Pi.

What was added to help:
- `src/movement.py`: a Movement class that uses `gpiozero.Motor` when available, or prints simulated actions when not.
- `src/keyboard_control.py`: a tiny curses-based keyboard driver (W/A/S/D or arrows, space to stop, q to quit).

How to run on the Pi:
1. Wire your motors to the motor driver and to the Pi's GPIO pins. Update pin numbers in `src/movement.py` if your wiring differs.
2. On the Pi, create and activate a venv and install requirements:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt gpiozero
  ```
3. Run the keyboard controller (in a real terminal connected to the Pi):
  ```bash
  python3 src/keyboard_control.py
  ```
Running in simulation locally
---------------------------
If you don't have the Pi hardware attached you can force the software simulation:

```bash
python3 src/keyboard_control.py --simulate
```

This will run the keyboard teleop using the Movement simulation instead of gpiozero.

Safety:
- Test at low speed first and clear the robot from obstacles.
- If you don't have hardware attached, the Movement methods will print simulated actions.

## Voice & Attitude
- Chatbot bridge with STT → Chat → TTS: `src/chatbot.py`
- Persona file (cracked saga WALL‑E vibe): `src/personas/wallee.txt`
- Quick launcher (local stdin or Pi audio): `scripts/talk_wallee.sh`

Examples:
```bash
# Local/dev (stdin, prints TTS)
bash scripts/talk_wallee.sh

# With OpenAI (uses persona as system prompt)
export OPENAI_API_KEY=... && bash scripts/talk_wallee.sh --no-sim
```

## Autonomy (Obstacle Avoidance)
Basic avoid‑obstacles loop using an ultrasonic sensor.

- Module: `src/autonomy.py`
- Sensor wrapper: `src/sensors.py` (uses `gpiozero.DistanceSensor` if available, else simulation)

Run:
```bash
# Simulation
python3 src/autonomy.py --simulate

# On Pi (example pins; choose pins that don't conflict with motors)
python3 src/autonomy.py --echo 24 --trigger 25
```

## Dependencies
- Install base deps: `pip install -r requirements.txt`
- On Raspberry Pi for motors/sensors: `pip install gpiozero` (or `sudo apt install python3-gpiozero`)
- Optional for voice: `pyttsx3`, `vosk`, `sounddevice`. For OpenAI: set `OPENAI_API_KEY`.

## Sync to Raspberry Pi
```bash
./scripts/sync_to_pi.sh pi@<pi-host> /home/pi/robot-project
```
Then SSH to the Pi and run the examples.
