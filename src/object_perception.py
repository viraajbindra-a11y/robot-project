"""Object perception helpers for WALL·E-style manipulation."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple, Union

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
    color: str
    shape: str
    distance_cm: float
    angle_deg: float  # positive == turn right, negative == turn left

    def friendly_label(self) -> str:
        return self.label.replace('_', ' ')

    def direction_hint(self) -> str:
        if self.angle_deg < -12:
            return 'to your left'
        if self.angle_deg > 12:
            return 'to your right'
        return 'straight ahead'

    def description(self) -> str:
        color = self.color.replace('_', ' ')
        shape = self.shape.replace('_', ' ')
        return (
            f"{color} {shape} ({self.friendly_label()}) about {self.distance_cm:.0f} cm away "
            f"{self.direction_hint()}"
        )

    def as_dict(self) -> Dict[str, object]:
        return {
            'label': self.label,
            'color': self.color,
            'shape': self.shape,
            'distance_cm': round(self.distance_cm, 2),
            'angle_deg': round(self.angle_deg, 2),
            'direction': self.direction_hint(),
        }


ColorSpec = Dict[str, Union[Tuple[int, int], str, Iterable[str]]]


DEFAULT_COLOR_MAP: Dict[str, ColorSpec] = {
    'red_cube': {
        'h': (0, 10),
        's': (120, 255),
        'v': (80, 255),
        'color': 'red',
        'shape': 'cube',
    },
    'green_cube': {
        'h': (40, 85),
        's': (120, 255),
        'v': (70, 255),
        'color': 'green',
        'shape': 'cube',
    },
    'blue_cube': {
        'h': (100, 135),
        's': (120, 255),
        'v': (70, 255),
        'color': 'blue',
        'shape': 'cube',
        'aliases': ('blue block', 'blue box'),
    },
    'yellow_sign': {
        'h': (20, 35),
        's': (120, 255),
        'v': (120, 255),
        'color': 'yellow',
        'shape': 'triangle',
        'aliases': ('warning sign', 'triangle sign'),
    },
    'orange_mug': {
        'h': (5, 25),
        's': (140, 255),
        'v': (120, 255),
        'color': 'orange',
        'shape': 'mug',
        'aliases': ('orange cup', 'mug', 'coffee mug'),
    },
    'black_box': {
        'h': (0, 180),
        's': (0, 80),
        'v': (0, 60),
        'color': 'black',
        'shape': 'box',
        'aliases': ('black block', 'black cube'),
    },
}


class ObjectRecognizer:
    """Rudimentary object recogniser with simulation fallback."""

    def __init__(
        self,
        *,
        simulate: bool = False,
        camera_index: int = 0,
        color_map: Optional[Dict[str, ColorSpec]] = None,
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
        label = self.resolve_label(label) or label.lower().replace(' ', '_')
        for obs in self.observations():
            if obs.label == label:
                return obs
        return None

    def resolve_label(self, query: str) -> Optional[str]:
        candidate = query.lower().strip().replace('-', ' ')
        candidate_key = candidate.replace(' ', '_')
        if candidate_key in self.color_map:
            return candidate_key
        for label in self.color_map:
            pretty_label = label.replace('_', ' ')
            if candidate in pretty_label:
                return label
            colour = self._colour_name(label)
            shape = self._shape_name(label)
            if colour in candidate and shape in candidate:
                return label
            for alias in self._aliases(label):
                alias_norm = alias.lower().replace('-', ' ')
                if candidate == alias_norm or candidate in alias_norm:
                    return label
        return None

    def describe(self, label: Optional[str] = None) -> str:
        if label:
            resolved = self.resolve_label(label)
            if not resolved:
                return f"I don't have a profile for a {label}."
            obs = self.locate(resolved)
            if obs:
                return f"I see {obs.description()}."
            friendly = resolved.replace('_', ' ')
            return f"I don't see a {friendly} right now."

        descriptions = self.describe_observations()
        if not descriptions:
            return "I don't see anything important right now."
        if len(descriptions) == 1:
            return f"I see {descriptions[0]}."
        if len(descriptions) == 2:
            return f"I see {descriptions[0]} and {descriptions[1]}."
        lead = ', '.join(descriptions[:-1])
        return f"I see {lead}, and {descriptions[-1]}."

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
                color=self._colour_name(label),
                shape=self._shape_name(label),
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
            shape = self._infer_shape(contour, w, h, self._shape_name(label))
            observations.append(
                ObjectObservation(
                    label=label,
                    color=self._colour_name(label),
                    shape=shape,
                    distance_cm=distance,
                    angle_deg=angle,
                )
            )
        return observations

    def describe_observations(self) -> List[str]:
        return [obs.description() for obs in self.observations()]

    def _colour_name(self, label: str) -> str:
        meta = self.color_map.get(label, {})
        if isinstance(meta, dict):
            colour = meta.get('color')  # type: ignore[arg-type]
            if colour:
                return str(colour)
        parts = label.split('_')
        return parts[0] if parts else label

    def _shape_name(self, label: str) -> str:
        meta = self.color_map.get(label, {})
        if isinstance(meta, dict):
            shape = meta.get('shape')  # type: ignore[arg-type]
            if shape:
                return str(shape)
        parts = label.split('_')
        return parts[-1] if len(parts) > 1 else 'object'

    def _aliases(self, label: str) -> Iterable[str]:
        meta = self.color_map.get(label, {})
        if not isinstance(meta, dict):
            return []
        aliases = meta.get('aliases')
        if isinstance(aliases, str):
            return [aliases]
        if isinstance(aliases, Iterable):
            return [str(item) for item in aliases]
        return []

    @staticmethod
    def _infer_shape(contour, width: float, height: float, default_shape: str) -> str:
        if cv2 is None:
            return default_shape
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
        sides = len(approx)
        if sides == 3:
            return 'triangle'
        if sides == 4:
            if height == 0:
                return 'rectangle'
            ratio = width / float(height)
            return 'square' if 0.9 <= ratio <= 1.1 else 'rectangle'
        if sides == 5:
            return 'pentagon'
        if sides >= 6:
            return 'circle'
        return default_shape
