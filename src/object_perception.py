"""Object perception helpers for WALL·E-style manipulation.

The recogniser supports three tiers of perception:

1.  Local colour/shape heuristics using OpenCV when available (multi-range HSV
    masks, contour analysis and shape inference with noise suppression).
2.  Remote inference via :class:`~src.remote_vision.RemoteVisionClient` when a
    cloud endpoint is configured.
3.  Deterministic simulation for development and testing.

Colour profiles can be extended at runtime or loaded from JSON configuration
files. Each profile can include multiple HSV ranges (covering wrap-around
colours such as red), human-friendly aliases and canonical colour/shape names
used for narration and control.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

try:  # pragma: no cover - optional runtime dependency
    import cv2
    import numpy as np
except Exception:  # pragma: no cover - keep simulation working without OpenCV
    cv2 = None  # type: ignore
    np = None  # type: ignore

LOGGER = logging.getLogger(__name__)

HSVRangeMapping = Dict[str, Tuple[int, int]]
ColorSpec = Dict[str, Union[Tuple[int, int], str, Iterable[str], List[HSVRangeMapping], HSVRangeMapping]]


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


DEFAULT_COLOR_MAP: Dict[str, ColorSpec] = {
    'red_cube': {
        'ranges': [
            {'h': (0, 10), 's': (150, 255), 'v': (90, 255)},
            {'h': (170, 179), 's': (150, 255), 'v': (90, 255)},
        ],
        'color': 'red',
        'shape': 'cube',
        'aliases': ('red block', 'red box'),
    },
    'green_cube': {
        'h': (40, 85),
        's': (120, 255),
        'v': (70, 255),
        'color': 'green',
        'shape': 'cube',
        'aliases': ('green block',),
    },
    'blue_cube': {
        'h': (100, 135),
        's': (120, 255),
        'v': (70, 255),
        'color': 'blue',
        'shape': 'cube',
        'aliases': ('blue block', 'blue box'),
    },
    'purple_ball': {
        'h': (130, 155),
        's': (150, 255),
        'v': (90, 255),
        'color': 'purple',
        'shape': 'ball',
        'aliases': ('purple sphere',),
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
        'aliases': ('orange cup', 'coffee mug'),
    },
    'black_box': {
        'h': (0, 180),
        's': (0, 80),
        'v': (0, 60),
        'color': 'black',
        'shape': 'box',
        'aliases': ('black block', 'black cube'),
    },
    'white_plate': {
        'h': (0, 180),
        's': (0, 30),
        'v': (180, 255),
        'color': 'white',
        'shape': 'plate',
        'aliases': ('white disc',),
    },
    'silver_can': {
        'ranges': [
            {'h': (0, 10), 's': (0, 70), 'v': (170, 255)},
            {'h': (170, 179), 's': (0, 70), 'v': (170, 255)},
        ],
        'color': 'silver',
        'shape': 'cylinder',
        'aliases': ('soda can', 'aluminium can'),
    },
    'green_cone': {
        'h': (45, 80),
        's': (170, 255),
        'v': (120, 255),
        'color': 'green',
        'shape': 'cone',
        'aliases': ('traffic cone',),
    },
}


class ObjectRecognizer:
    """Rudimentary object recogniser with simulation fallback and remote support."""

    def __init__(
        self,
        *,
        simulate: bool = False,
        camera_index: int = 0,
        color_map: Optional[Dict[str, ColorSpec]] = None,
        remote_client: Optional[object] = None,
    ) -> None:
        self.simulate = simulate or cv2 is None or np is None
        self.camera_index = camera_index
        self.color_map = self._normalise_color_map(color_map or DEFAULT_COLOR_MAP)
        self.remote_client = remote_client
        self._cap = None
        if not self.simulate and cv2 is not None:
            self._cap = cv2.VideoCapture(camera_index)
            if not self._cap or not self._cap.isOpened():
                LOGGER.warning("Failed to open camera %s, falling back to simulation", camera_index)
                self.simulate = True

    # ------------------------------------------------------------------ API

    def observations(self) -> List[ObjectObservation]:
        remote_observations = self._detect_remote()
        if remote_observations:
            return remote_observations
        if self.simulate:
            return self._simulate_observations()
        return self._detect_colours()

    def locate(self, label: str) -> Optional[ObjectObservation]:
        resolved = self.resolve_label(label) or label.lower().replace(' ', '_')
        for obs in self.observations():
            if obs.label == resolved:
                return obs
        return None

    def resolve_label(self, query: str) -> Optional[str]:
        candidate = query.lower().strip().replace('-', ' ')
        candidate_key = candidate.replace(' ', '_')
        if candidate_key in self.color_map:
            return candidate_key
        for label, profile in self.color_map.items():
            pretty = label.replace('_', ' ')
            if candidate in pretty:
                return label
            if profile['color'] in candidate and profile['shape'] in candidate:
                return label
            for alias in profile['aliases']:
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

    def describe_observations(self) -> List[str]:
        return [obs.description() for obs in self.observations()]

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

    # ---------------------------------------------------------------- simulation

    def _simulate_observations(self) -> List[ObjectObservation]:
        labels = list(self.color_map.keys())
        if not labels:
            return []
        num_objects = random.randint(0, len(labels))
        chosen = random.sample(labels, num_objects) if num_objects else []
        return [
            ObjectObservation(
                label=label,
                color=profile['color'],
                shape=profile['shape'],
                distance_cm=random.uniform(10.0, 60.0),
                angle_deg=random.uniform(-45.0, 45.0),
            )
            for label, profile in ((lab, self.color_map[lab]) for lab in chosen)
        ]

    # ---------------------------------------------------------------- detection

    def _detect_remote(self) -> List[ObjectObservation]:
        if not self.remote_client:
            return []
        try:
            payload = self.remote_client.detect()
        except Exception as exc:  # pragma: no cover - network failure
            LOGGER.warning("Remote vision failed: %s", exc)
            return []
        observations: List[ObjectObservation] = []
        for item in payload or []:
            if not isinstance(item, dict):
                continue
            label = item.get('label')
            if not isinstance(label, str):
                continue
            resolved = self.resolve_label(label) or label.lower().replace(' ', '_')
            profile = self.color_map.get(resolved, {
                'color': resolved.split('_')[0] if '_' in resolved else resolved,
                'shape': resolved.split('_')[-1] if '_' in resolved else 'object',
            })
            distance = float(item.get('distance_cm', item.get('distance', 0.0)))
            angle = float(item.get('angle_deg', item.get('angle', 0.0)))
            observations.append(
                ObjectObservation(
                    label=resolved,
                    color=profile.get('color', resolved),
                    shape=profile.get('shape', 'object'),
                    distance_cm=max(distance, 0.0),
                    angle_deg=angle,
                )
            )
        return observations

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
        kernel = np.ones((5, 5), np.uint8)
        observations: List[ObjectObservation] = []
        for label, profile in self.color_map.items():
            masks: List[np.ndarray] = []
            for hsv_range in profile['ranges']:
                lower = np.array([hsv_range['h'][0], hsv_range['s'][0], hsv_range['v'][0]])
                upper = np.array([hsv_range['h'][1], hsv_range['s'][1], hsv_range['v'][1]])
                masks.append(cv2.inRange(hsv, lower, upper))
            if not masks:
                continue
            mask = masks[0]
            for extra in masks[1:]:
                mask = cv2.bitwise_or(mask, extra)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
            contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(contour)
            if area < 80:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            center_x = x + w / 2
            angle = (center_x - (width / 2)) / max(width / 2, 1) * 45.0
            distance = self._estimate_distance(area, width * height)
            shape = self._infer_shape(contour, w, h, profile['shape'])
            observations.append(
                ObjectObservation(
                    label=label,
                    color=profile['color'],
                    shape=shape,
                    distance_cm=distance,
                    angle_deg=angle,
                )
            )
        return observations

    # ---------------------------------------------------------------- helpers

    def _aliases(self, label: str) -> Iterable[str]:
        return self.color_map.get(label, {}).get('aliases', [])

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

    @staticmethod
    def _estimate_distance(contour_area: float, frame_area: float) -> float:
        if frame_area <= 0 or contour_area <= 0:
            return 60.0
        coverage = contour_area / frame_area
        distance = 200.0 * (coverage ** -0.5)
        return max(8.0, min(distance, 120.0))

    # ---------------------------------------------------------------- config

    @staticmethod
    def load_color_map(path: Union[str, Path]) -> Dict[str, ColorSpec]:
        """Load a colour profile JSON file."""

        with Path(path).expanduser().open('r', encoding='utf-8') as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError('Colour map JSON must map labels to profiles')
        return ObjectRecognizer._normalise_color_map(data)

    @staticmethod
    def _normalise_color_map(raw_map: Dict[str, ColorSpec]) -> Dict[str, Dict[str, object]]:
        normalised: Dict[str, Dict[str, object]] = {}
        for label, spec in raw_map.items():
            if not isinstance(spec, dict):
                raise ValueError(f'Colour profile for {label} must be a dict')
            colour = str(spec.get('color', label.split('_')[0] if '_' in label else label))
            shape = str(spec.get('shape', label.split('_')[-1] if '_' in label else 'object'))
            aliases = spec.get('aliases', [])
            if isinstance(aliases, str):
                aliases = [aliases]
            elif isinstance(aliases, Iterable):
                aliases = [str(a) for a in aliases]
            else:
                aliases = []

            ranges: List[HSVRangeMapping] = []
            if 'ranges' in spec:
                raw_ranges = spec['ranges']
                if isinstance(raw_ranges, dict):
                    raw_ranges = [raw_ranges]
                for entry in raw_ranges:
                    ranges.append(ObjectRecognizer._validate_hsv(entry, label))
            elif all(key in spec for key in ('h', 's', 'v')):
                ranges.append(ObjectRecognizer._validate_hsv({'h': spec['h'], 's': spec['s'], 'v': spec['v']}, label))
            else:
                raise ValueError(f'Colour profile for {label} lacks HSV range information')

            normalised[label] = {
                'color': colour,
                'shape': shape,
                'aliases': tuple(aliases),
                'ranges': ranges,
            }
        return normalised

    @staticmethod
    def _validate_hsv(entry: ColorSpec, label: str) -> HSVRangeMapping:
        try:
            h = tuple(entry['h'])  # type: ignore[index]
            s = tuple(entry['s'])  # type: ignore[index]
            v = tuple(entry['v'])  # type: ignore[index]
        except Exception as exc:  # pragma: no cover - config error
            raise ValueError(f'Invalid HSV range for {label}: {entry}') from exc
        if any(len(x) != 2 for x in (h, s, v)):
            raise ValueError(f'HSV tuples must have two values for {label}')
        return {'h': (int(h[0]), int(h[1])), 's': (int(s[0]), int(s[1])), 'v': (int(v[0]), int(v[1]))}

    def update_color_map(self, extra: Dict[str, ColorSpec]) -> None:
        """Merge additional colour profiles into the recogniser."""

        self.color_map.update(self._normalise_color_map(extra))
