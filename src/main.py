"""Master control loop tying together chatbot, movement, autonomy, gestures, gripper, and perception."""

from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Tuple

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.auto_drive import AutoDriver
from src.battery_check import BatteryConfig, BatteryMonitor
from src.chatbot import Chatbot
from src.gesture_control import GestureController
from src.gripper_control import GripperController
from src.movement import Movement
from src.object_perception import ObjectRecognizer
from src.remote_vision import RemoteVisionClient
from src.cloud_vision import GoogleVisionClient, DEFAULT_ENDPOINT as GOOGLE_DEFAULT_ENDPOINT
from src.personality_adapter import PersonalityAdapter, DEFAULT_PERSONA, load_persona_from_file
from src.safe_shutdown import SafeShutdown
from src.sensors import DistanceSensorWrapper
from src.utils.adc import ADS1115Config, create_voltage_reader
from src.voice import Voice
from src.wall_guard import WallGuard

LOGGER = logging.getLogger(__name__)


def parse_pins(pins: Sequence[int], expected: int, description: str) -> Tuple[int, ...]:
    if len(pins) != expected:
        raise ValueError(f"Expected {expected} values for {description}, got {pins}")
    return tuple(int(p) for p in pins)


def run_master(
    *,
    simulate: bool,
    persona_path: Optional[str],
    enable_autonomy: bool,
    left_pins: Tuple[int, int],
    right_pins: Tuple[int, int],
    battery_driver: str,
    battery_env_var: str,
    battery_env_default: float,
    battery_ads_channel: int,
    battery_ads_gain: int,
    battery_divider_ratio: float,
    sensor_echo: Optional[int],
    sensor_trigger: Optional[int],
    left_servo_pin: Optional[int],
    right_servo_pin: Optional[int],
    gripper_pin: Optional[int],
    camera_index: int,
    vision_endpoint: Optional[str],
    vision_key: Optional[str],
    google_vision_key: Optional[str],
    google_vision_endpoint: Optional[str],
    google_vision_features: Optional[Sequence[str]],
    color_config_path: Optional[str],
) -> None:
    logging.basicConfig(level=logging.INFO)

    persona = DEFAULT_PERSONA
    persona_text: Optional[str] = None
    if persona_path:
        try:
            persona = load_persona_from_file(persona_path)
            persona_text = "\n".join(f"{k}={v}" for k, v in persona.items())
        except Exception as exc:
            LOGGER.warning("Failed to load persona %s: %s", persona_path, exc)

    adapter = PersonalityAdapter(persona)
    movement = Movement(left_pins=left_pins, right_pins=right_pins, simulate=simulate)
    voice = Voice(simulate=simulate)
    chatbot = Chatbot(attitude=persona.get('tone', 'friendly'), simulate=True, control_mode=True)
    gesture_controller = GestureController(
        left_servo_pin=left_servo_pin,
        right_servo_pin=right_servo_pin,
        simulate=simulate,
    )
    gripper = GripperController(pin=gripper_pin, simulate=simulate)

    remote_client: Optional[RemoteVisionClient] = None
    if vision_endpoint and vision_key and not simulate:
        try:
            remote_client = RemoteVisionClient(api_url=vision_endpoint, api_key=vision_key, camera_index=camera_index)
        except Exception as exc:
            LOGGER.warning("Remote vision unavailable (%s); falling back to local/simulated perception", exc)
            remote_client = None

    google_client = None
    if google_vision_key and not simulate:
        try:
            google_client = GoogleVisionClient(
                api_key=google_vision_key,
                camera_index=camera_index,
                endpoint=google_vision_endpoint or GOOGLE_DEFAULT_ENDPOINT,
                features=google_vision_features,
            )
        except Exception as exc:
            LOGGER.warning("Google Vision unavailable (%s); continuing without it", exc)
            google_client = None

    color_override = None
    if color_config_path:
        try:
            color_override = ObjectRecognizer.load_color_map(color_config_path)
        except Exception as exc:
            LOGGER.warning("Failed to load colour map %s: %s", color_config_path, exc)

    recognizer = ObjectRecognizer(
        simulate=simulate,
        camera_index=camera_index,
        color_map=color_override,
        remote_client=google_client or remote_client,
    )

    front_sensor: Optional[DistanceSensorWrapper] = None
    wall_guard: Optional[WallGuard] = None
    if sensor_echo is not None and sensor_trigger is not None:
        front_sensor = DistanceSensorWrapper(
            echo=sensor_echo,
            trigger=sensor_trigger,
            simulate=simulate,
        )
        wall_guard = WallGuard(front_sensor)

    ads_config = ADS1115Config(
        channel=battery_ads_channel,
        gain=battery_ads_gain,
        voltage_divider_ratio=battery_divider_ratio,
    )
    reader = create_voltage_reader(
        battery_driver,
        env_var=battery_env_var,
        env_default=battery_env_default,
        ads_config=ads_config,
    )
    monitor = BatteryMonitor(reader, config=BatteryConfig())
    shutdown = SafeShutdown(monitor, movement=movement, simulate=simulate)

    auto_state: Dict[str, Optional[object]] = {'driver': None, 'thread': None, 'sensor': None, 'owns_sensor': None}

    def start_autonomy() -> None:
        if auto_state['driver'] is not None:
            return
        if front_sensor is not None:
            driver = AutoDriver(movement=movement, sensor=front_sensor, manage_sensor=False)
            auto_state['sensor'] = front_sensor
            auto_state['owns_sensor'] = False
        else:
            sensor = DistanceSensorWrapper(
                echo=sensor_echo,
                trigger=sensor_trigger,
                simulate=simulate or sensor_echo is None or sensor_trigger is None,
            )
            driver = AutoDriver(movement=movement, sensor=sensor, manage_sensor=True)
            auto_state['sensor'] = sensor
            auto_state['owns_sensor'] = True
        auto_state['driver'] = driver
        thread = threading.Thread(target=driver.run, daemon=True)
        auto_state['thread'] = thread
        thread.start()

    def stop_autonomy() -> None:
        driver = auto_state['driver']
        thread = auto_state['thread']
        sensor = auto_state['sensor']
        if driver is None:
            return
        driver.stop()
        if thread:
            thread.join(timeout=1.0)
        if auto_state.get('owns_sensor') and sensor:
            sensor.close()
        auto_state['driver'] = None
        auto_state['thread'] = None
        auto_state['sensor'] = None
        auto_state['owns_sensor'] = None

    current_motion = {'value': 'stop'}

    def apply_movement(action: str) -> None:
        if action == 'forward':
            movement.move_forward()
        elif action == 'backward':
            movement.move_backward()
        elif action == 'left':
            movement.turn_left()
        elif action == 'right':
            movement.turn_right()
        elif action == 'stop':
            movement.stop()
        current_motion['value'] = action

    def apply_tuning(action_value: str) -> None:
        if action_value.startswith('speed_set:'):
            try:
                movement.set_speed_scale(float(action_value.split(':', 1)[1]))
            except ValueError:
                LOGGER.debug('Invalid speed_set value: %s', action_value)
        elif action_value.startswith('speed_adj:'):
            try:
                movement.adjust_speed_scale(float(action_value.split(':', 1)[1]))
            except ValueError:
                LOGGER.debug('Invalid speed_adj value: %s', action_value)
        elif action_value == 'trim_reset':
            movement.reset_trim()
        elif action_value.startswith('trim_set:'):
            try:
                _, side, amount = action_value.split(':', 2)
                value = float(amount)
            except ValueError:
                LOGGER.debug('Invalid trim_set value: %s', action_value)
                return
            if side == 'left':
                movement.set_trim(value, movement.trim[1])
            elif side == 'right':
                movement.set_trim(movement.trim[0], value)
        elif action_value.startswith('trim_adj:'):
            try:
                _, side, amount = action_value.split(':', 2)
                value = float(amount)
            except ValueError:
                LOGGER.debug('Invalid trim_adj value: %s', action_value)
                return
            if side == 'left':
                movement.adjust_trim(left_delta=value)
            elif side == 'right':
                movement.adjust_trim(right_delta=value)

    def execute(actions: Iterable[Dict[str, str]]) -> None:
        for action in actions:
            typ = action.get('type')
            value = action.get('value', '')
            if typ == 'movement' and value:
                if value == 'forward' and wall_guard and not wall_guard.allows_forward():
                    movement.stop()
                    current_motion['value'] = 'stop'
                    voice.speak(adapter.apply("Wall ahead, stopping."))
                    continue
                apply_movement(value)
            elif typ == 'autonomy' and value:
                if value == 'start':
                    start_autonomy()
                elif value == 'stop':
                    stop_autonomy()
            elif typ == 'gesture' and value:
                gesture_controller.perform(value)
            elif typ == 'gripper' and value:
                if value == 'close':
                    gripper.close()
                elif value == 'open':
                    gripper.open()
                elif value == 'toggle':
                    gripper.toggle()
            elif typ == 'arms' and value:
                parts = value.split(':')
                if len(parts) == 3:
                    mode, left_raw, right_raw = parts
                    try:
                        left_val = float(left_raw)
                        right_val = float(right_raw)
                    except ValueError:
                        continue
                    if mode == 'set':
                        gesture_controller.set_positions(left_val, right_val)
                    elif mode == 'set_left':
                        current_left, current_right = gesture_controller.positions
                        gesture_controller.set_positions(left_val, current_right)
                   elif mode == 'set_right':
                       current_left, current_right = gesture_controller.positions
                       gesture_controller.set_positions(current_left, right_val)
                   elif mode == 'adjust':
                       gesture_controller.adjust(left_val, right_val)
            elif typ == 'tuning' and value:
                apply_tuning(value)
            elif typ == 'task' and value:
                if value.startswith('grab:'):
                    label = value.split(':', 1)[1]
                    plan = recognizer.plan_grab(label)
                    execute(plan)
            elif typ == 'vision':
                label = None
                if value and ':' in value:
                    _, detail = value.split(':', 1)
                    label = detail
                speech = recognizer.describe(label)
                voice.speak(adapter.apply(speech))
            elif typ == 'speech' and value:
                voice.speak(adapter.apply(value))

    def battery_thread() -> None:
        shutdown.monitor_loop(interval_s=15.0)

    thread = threading.Thread(target=battery_thread, daemon=True)
    thread.start()

    if enable_autonomy:
        start_autonomy()

    guard_running = True
    guard_flag = {'notified': False}

    def guard_loop() -> None:
        if not wall_guard:
            return
        while guard_running:
            if current_motion['value'] == 'forward':
                if not wall_guard.allows_forward():
                    movement.stop()
                    current_motion['value'] = 'stop'
                    if not guard_flag['notified']:
                        voice.speak(adapter.apply("Wall ahead, stopping."))
                        guard_flag['notified'] = True
                else:
                    guard_flag['notified'] = False
            else:
                guard_flag['notified'] = False
            time.sleep(0.1)

    guard_thread = None
    if wall_guard:
        guard_thread = threading.Thread(target=guard_loop, daemon=True)
        guard_thread.start()

    try:
        while True:
            text = voice.listen(timeout=5.0, phrase_time_limit=5.0)
            if not text:
                continue
            lower = text.lower()
            if lower in ('quit', 'shutdown', 'power down'):
                voice.speak(adapter.apply("Shutting down systems."))
                break
            control = chatbot.generate_control_reply(text, persona_text=persona_text)
            speech = adapter.apply(control.get('speech', ''))
            if speech:
                voice.speak(speech)
            execute(control.get('actions', []))
    except KeyboardInterrupt:
        LOGGER.info("Master loop interrupted")
    finally:
        guard_running = False
        if guard_thread:
            guard_thread.join(timeout=0.5)
        stop_autonomy()
        shutdown.cancel()
        movement.stop()
        gesture_controller.close()
        gripper.close_controller()
        recognizer.close()
        if remote_client:
            try:
                remote_client.close()
            except Exception:
                pass
        if google_client:
            try:
                google_client.close()
            except Exception:
                pass
        if wall_guard:
            wall_guard.close()


def main() -> None:
    parser = argparse.ArgumentParser(description='Master control loop')
    parser.add_argument('--simulate', action='store_true')
    parser.add_argument('--persona')
    parser.add_argument('--auto', action='store_true', help='Enable obstacle avoidance in parallel')
    parser.add_argument('--left-pins', nargs=2, type=int, default=[17, 18], metavar=('FWD', 'REV'))
    parser.add_argument('--right-pins', nargs=2, type=int, default=[22, 23], metavar=('FWD', 'REV'))
    parser.add_argument('--sensor-echo', type=int, help='BCM pin for ultrasonic echo')
    parser.add_argument('--sensor-trigger', type=int, help='BCM pin for ultrasonic trigger')
    parser.add_argument('--battery-driver', choices=['env', 'ads1115'], default='env')
    parser.add_argument('--battery-env', default='ROBOT_BATTERY_VOLTS')
    parser.add_argument('--battery-env-default', type=float, default=12.0)
    parser.add_argument('--battery-ads-channel', type=int, default=0)
    parser.add_argument('--battery-ads-gain', type=int, default=1)
    parser.add_argument('--battery-divider-ratio', type=float, default=2.0)
    parser.add_argument('--left-servo', type=int, help='BCM pin for left arm servo')
    parser.add_argument('--right-servo', type=int, help='BCM pin for right arm servo')
    parser.add_argument('--gripper-servo', type=int, help='BCM pin for gripper claw servo')
    parser.add_argument('--camera-index', type=int, default=0, help='Camera index for object perception')
    parser.add_argument('--vision-endpoint', help='URL of the remote vision API')
    parser.add_argument('--vision-key', help='API key/token for the remote vision API')
    parser.add_argument('--google-vision-key', help='Google Vision API key (OBJECT_LOCALIZATION)')
    parser.add_argument('--google-vision-endpoint', help='Custom Google Vision endpoint override')
    parser.add_argument('--google-vision-features', nargs='*', help='Google Vision feature list (default OBJECT_LOCALIZATION)')
    parser.add_argument('--vision-colors', help='Path to JSON colour profile for perception')
    args = parser.parse_args()

    run_master(
        simulate=args.simulate,
        persona_path=args.persona,
        enable_autonomy=args.auto,
        left_pins=parse_pins(args.left_pins, 2, 'left motor pins'),
        right_pins=parse_pins(args.right_pins, 2, 'right motor pins'),
        battery_driver=args.battery_driver,
        battery_env_var=args.battery_env,
        battery_env_default=args.battery_env_default,
        battery_ads_channel=args.battery_ads_channel,
        battery_ads_gain=args.battery_ads_gain,
        battery_divider_ratio=args.battery_divider_ratio,
        sensor_echo=args.sensor_echo,
        sensor_trigger=args.sensor_trigger,
        left_servo_pin=args.left_servo,
        right_servo_pin=args.right_servo,
        gripper_pin=args.gripper_servo,
        camera_index=args.camera_index,
        vision_endpoint=args.vision_endpoint,
        vision_key=args.vision_key,
        google_vision_key=args.google_vision_key,
        google_vision_endpoint=args.google_vision_endpoint,
        google_vision_features=args.google_vision_features,
        color_config_path=args.vision_colors,
    )


if __name__ == '__main__':
    main()
