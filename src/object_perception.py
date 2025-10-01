"""Object perception helpers for WALL·E-style manipulation."""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

try:  # pragma: no cover - optional runtime dependency
    import cv2
    import numpy as np
except Exception:  # pragma: no cover - keep simulation working without OpenCV
    cv2 = None  # type: ignore
    np = None  # type: ignore

LOGGER = logging.getLogger(__name__)


@dataclass
class ObjectObservation:
    label: str
    distance_cm: float
    angle_deg: float  # positive == turn right, negative == turn left


DEFAULT_COLOR_MAP: Dict[str, Dict[str, Tuple[int, int]]] = {
    'red_cube': {'h': (0, 10), 's': (120, 255), 'v': (80, 255)},
    'green_cube': {'h': (40, 85), 's': (120, 255), 'v': (70, 255)},
    'blue_cube': {'h': (100, 135), 's': (120, 255), 'v': (70, 255)},
}


class ObjectRecognizer:
    """Rudimentary object recogniser with simulation fallback."""

    def __init__(
        self,
        *,
        simulate: bool = False,
        camera_index: int = 0,
        color_map: Optional[Dict[str, Dict[str, Tuple[int, int]]]] = None,
    ) -> None:
        self.simulate = simulate or cv2 is None or np is None
        self.camera_index = camera_index
        self.color_map = color_map or DEFAULT_COLOR_MAP
        self._cap = None
        if not self.simulate and cv2 is not None:
            self._cap = cv2.VideoCapture(camera_index)
            if not self._cap or not self._cap.isOpened():
                LOGGER.warning("Failed to open camera %s, falling back to simulation", camera_index)
                self.simulate = True

    def observations(self) -> List[ObjectObservation]:
        if self.simulate:
            return self._simulate_observations()
        return self._detect_colours()

    def locate(self, label: str) -> Optional[ObjectObservation]:
        label = label.lower().replace(' ', '_')
        for obs in self.observations():
            if obs.label == label:
                return obs
        return None

    def plan_grab(self, label: str) -> List[Dict[str, str]]:
        obs = self.locate(label)
        if not obs:
            LOGGER.info("Object '%s' not found", label)
            return [{'type': 'speech', 'value': f"I can't find a {label.replace('_', ' ')}."}]

        actions: List[Dict[str, str]] = []
        if abs(obs.angle_deg) > 15:
            direction = 'left' if obs.angle_deg < 0 else 'right'
            actions.append({'type': 'movement', 'value': direction})
        if obs.distance_cm > 15:
            actions.append({'type': 'movement', 'value': 'forward'})
        actions.append({'type': 'movement', 'value': 'stop'})
        actions.append({'type': 'gripper', 'value': 'close'})
        return actions

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()

    # ------------------------------------------------------------------

    def _simulate_observations(self) -> List[ObjectObservation]:
        labels = list(self.color_map.keys())
        if not labels:
            return []
        num_objects = random.randint(0, len(labels))
        chosen = random.sample(labels, num_objects) if num_objects else []
        return [
            ObjectObservation(
                label=label,
                distance_cm=random.uniform(10.0, 60.0),
                angle_deg=random.uniform(-45.0, 45.0),
            )
            for label in chosen
        ]

    def _detect_colours(self) -> List[ObjectObservation]:  # pragma: no cover
        assert cv2 is not None and np is not None
        if not self._cap:
            return []
        success, frame = self._cap.read()
        if not success:
            LOGGER.warning("Failed to read frame from camera")
            return []
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        height, width = hsv.shape[:2]
        observations: List[ObjectObservation] = []
        for label, ranges in self.color_map.items():
            lower = np.array([ranges['h'][0], ranges['s'][0], ranges['v'][0]])
            upper = np.array([ranges['h'][1], ranges['s'][1], ranges['v'][1]])
            mask = cv2.inRange(hsv, lower, upper)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
            contour = max(contours, key=cv2.contourArea)
            if cv2.contourArea(contour) < 50:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            center_x = x + w / 2
            angle = (center_x - (width / 2)) / (width / 2) * 45.0
            relative_size = (w * h) / float(width * height)
            distance = max(10.0, 100.0 - relative_size * 400.0)
            observations.append(ObjectObservation(label=label, distance_cm=distance, angle_deg=angle))
        return observations
