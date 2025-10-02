# Robot Project

## Overview
This project is designed to control a robot using movement and voice functionalities. It serves as a foundation
for building more complex robotic applications.

## Project Structure
```
robot-project
├── src
│   ├── main.py                # Master control loop tying all subsystems together
│   ├── movement.py            # Differential drive helper (simulation + gpiozero)
│   ├── pwm_control.py         # Fine-grained PWM motor speed helper
│   ├── auto_drive.py          # Obstacle avoidance driver
│   ├── ultrasonic_test.py     # CLI distance sampler
│   ├── obstacle_avoid.py      # Obstacle avoidance CLI runner
│   ├── battery_check.py       # Battery voltage monitor utilities
│   ├── safe_shutdown.py       # Critical battery handling and shutdown
│   ├── voice.py               # Speech I/O abstraction
│   ├── tts_test.py / stt_test.py  # Quick voice diagnostics
│   ├── voice_drive.py         # Voice → movement teleop
│   ├── attitude_drive.py      # Personality-aware teleop
│   ├── camera_vision.py       # Optional OpenCV helper
│   ├── vision_chat.py         # Camera + persona demo loop
│   ├── object_perception.py   # Colour-based object perception with simulation fallback
│   ├── gesture_control.py     # Servo gesture poses
│   ├── gripper_control.py     # Simple servo gripper controller
│   ├── personality_adapter.py # WALL·E-style response shaping
│   └── utils
│       ├── __init__.py
│       └── adc.py             # Optional ADS1115 voltage reader
├── tests                      # Unit test suite for each module
├── scripts
│   ├── setup_pi.sh            # Bootstraps a Raspberry Pi with system deps
│   └── sync_to_pi.sh          # Synchronize files to Raspberry Pi
├── requirements.txt
└── README.md
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
3. (Optional) On Raspberry Pi, run the bootstrap script once:
  ```bash
  sudo ./scripts/setup_pi.sh
  ```
4. Install the required Python dependencies (in your venv if using one):
  ```bash
  pip install -r requirements.txt
  ```

## Usage
- Master control loop (chatbot-in-the-loop, runs voice → ChatGPT → actions):
  ```bash
  python3 src/main.py --simulate
  ```
  Toggle autonomy directly in conversation (“start autonomy”, “stop autonomy”). On hardware add `--auto`, supply sensor pins (`--sensor-echo 24 --sensor-trigger 25` for example), arm servo pins (`--left-servo 5 --right-servo 6`), an optional gripper servo (`--gripper-servo 12`), and set motor/battery flags as needed. For camera-based grab planning plug in a USB camera and pass `--camera-index 0` (default).
- Voice teleop:
  ```bash
  python3 src/voice_drive.py --simulate
  ```
- Personality + movement loop:
  ```bash
  python3 src/attitude_drive.py --persona src/personas/wallee.txt
  ```
- Obstacle avoidance and sensors:
  ```bash
  python3 src/obstacle_avoid.py --echo 24 --trigger 25
  python3 src/ultrasonic_test.py --echo 24 --trigger 25
  ```
- Diagnostics for speech I/O:
  ```bash
  python3 src/tts_test.py "Hello human"
  python3 src/stt_test.py --timeout 3
  ```

## Testing
- Run the entire suite:
  ```bash
  python3 -m unittest discover -s tests -p "*_test.py"
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
- Structured control mode (returns JSON directives for the master loop):
  ```bash
  python3 src/chatbot.py --simulate --control --persona-file src/personas/wallee.txt
  ```
  Useful for validating how conversations map to movement/autonomy/gesture/gripper commands.
- Ask the master loop things like “What do you see?” or “Do you see the orange mug?” to hear spoken object descriptions sourced from `ObjectRecognizer`.

Examples:
```bash
# Local/dev (stdin, prints TTS)
bash scripts/talk_wallee.sh

# With OpenAI (uses persona as system prompt)
export OPENAI_API_KEY=... && bash scripts/talk_wallee.sh --no-sim
```

## Autonomy (Obstacle Avoidance)
Basic avoid‑obstacles loop using an ultrasonic sensor.

- Module: `src/autonomy.py` / `src/auto_drive.py`
- Sensor wrapper: `src/sensors.py` (uses `gpiozero.DistanceSensor` if available, else simulation)
- CLI helpers: `src/ultrasonic_test.py`, `src/obstacle_avoid.py`
- Wall guard: `src/wall_guard.py` automatically halts forward motion when the front sensor says the path is too close.

Run:
```bash
# Simulation
python3 src/obstacle_avoid.py --simulate

# On Pi (example pins; choose pins that don't conflict with motors)
python3 src/obstacle_avoid.py --echo 24 --trigger 25
```

## Motor Tuning
- Runtime speed scaling and per-motor trim live in `src/movement.py`.
- Voice commands like “set speed to 0.6”, “speed up a bit”, “trim left motor by 0.05”, or “balance the motors” adjust the drivetrain while the master loop is running.
- You can reset trims by saying “reset trim” or via direct API calls (`Movement.reset_trim()`).

## Object Perception
- Module: `src/object_perception.py`
- Recognises simple coloured shapes (cubes, cones/signs) via OpenCV when available, with a simulation fallback and Google Vision integration.
- Call `ObjectRecognizer.describe_observations()` to get quick natural-language descriptions (colour, shape, distance, direction).
- Supply a custom colour-profile JSON via `--vision-colors path/to/colors.json`. Remote APIs (see `src/remote_vision.py`) feed into the same narration pipeline.
- Google Cloud Vision support: add `--google-vision-key $KEY` (and optionally `--google-vision-features OBJECT_LOCALIZATION`) to delegate perception to the cloud while keeping narration local.

## Power & Safety
- Battery monitor utilities: `src/battery_check.py`
- Safe shutdown helper: `src/safe_shutdown.py`
- Optional ADS1115 reader: `src/utils/adc.py` (install `adafruit-circuitpython-ads1x15`)

Expose the current voltage via environment variable (no ADC):
```bash
export ROBOT_BATTERY_VOLTS=12.4
python3 src/main.py --battery-driver env
```

Using ADS1115 (channel 0, gain 1) with a 2:1 voltage divider:
```bash
python3 src/main.py --battery-driver ads1115 --battery-ads-channel 0 --battery-divider-ratio 2.0
```

## Vision & Gestures
- Camera helper and demo loop: `src/camera_vision.py`, `src/vision_chat.py`
- Servo gestures and raw arm control: `src/gesture_control.py`
- Gripper control: `src/gripper_control.py`
- Chatbot-triggered poses and grip: ask the robot to “wave”, “salute”, “nod”, “grab that cube”, or “release it” while `src/main.py` is running. You can now say “set left arm to 0.5”, “raise both arms”, or “lower right arm” for precise positioning.
- Install `opencv-python` for vision and compatible servo drivers for arms/grippers.

## Dependencies
- Install base deps: `pip install -r requirements.txt`
- On Raspberry Pi for motors/sensors: `pip install gpiozero` (or `sudo apt install python3-gpiozero`)
- Optional for voice: `pyttsx3`, `vosk`, `sounddevice`, `pyaudio`. For OpenAI: set `OPENAI_API_KEY`.
- Optional for vision: `opencv-python` (or `sudo apt install python3-opencv`).

## Sync to Raspberry Pi
```bash
./scripts/sync_to_pi.sh pi@<pi-host> /home/pi/robot-project
```
Then SSH to the Pi and run the examples.
