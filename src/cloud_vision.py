"""Google Cloud Vision client wrapper for object localization.

This module provides a drop-in remote client compatible with
``ObjectRecognizer``. It captures frames using OpenCV, calls the Google
Vision ``images:annotate`` endpoint, and converts the response into the
shape expected by the perception pipeline (label, distance estimate,
angle).

Usage:
    client = GoogleVisionClient(api_key="...", camera_index=0)
    detections = client.detect()

The caller is responsible for shutting the client down by invoking
``close()`` when finished.
"""

from __future__ import annotations

import base64
import logging
from typing import Iterable, List, Optional

try:  # pragma: no cover - optional dependency
    import cv2
    import requests
except Exception:  # pragma: no cover - allow import without deps
    cv2 = None  # type: ignore
    requests = None  # type: ignore

LOGGER = logging.getLogger(__name__)

_DEFAULT_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"
_DEFAULT_FEATURES = ("OBJECT_LOCALIZATION",)

DEFAULT_ENDPOINT = _DEFAULT_ENDPOINT
DEFAULT_FEATURES = _DEFAULT_FEATURES


class GoogleVisionClient:
    """Capture frames and call the Google Cloud Vision API."""

    def __init__(
        self,
        *,
        api_key: str,
        camera_index: int = 0,
        endpoint: str = _DEFAULT_ENDPOINT,
        features: Optional[Iterable[str]] = None,
        max_results: int = 10,
    ) -> None:
        if cv2 is None or requests is None:
            raise RuntimeError(
                "GoogleVisionClient requires opencv-python and requests. "
                "Install them with `pip install opencv-python requests`."
            )
        self.api_key = api_key
        self.endpoint = endpoint
        self.features = tuple(features) if features else _DEFAULT_FEATURES
        self.max_results = max_results
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera index {camera_index}")

    # ------------------------------------------------------------------ public

    def detect(self) -> List[dict]:
        """Return detections as a list of dictionaries.

        Each detection dictionary contains:
            label: str
            distance_cm: float (rough estimate)
            angle_deg: float (rough heading)
        """

        frame = self.snapshot_jpeg()
        payload = self._build_payload(frame)
        params = {'key': self.api_key}
        resp = requests.post(self.endpoint, json=payload, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return self._parse_response(data)

    def close(self) -> None:
        if self.cap:
            self.cap.release()
            self.cap = None

    # ----------------------------------------------------------------- helpers

    def snapshot_jpeg(self) -> bytes:
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("Failed to capture frame from camera")
        ok, buffer = cv2.imencode('.jpg', frame)
        if not ok:
            raise RuntimeError("Failed to encode frame to JPEG")
        return buffer.tobytes()

    def _build_payload(self, frame_bytes: bytes) -> dict:
        image_content = base64.b64encode(frame_bytes).decode('utf-8')
        feature_list = [
            {'type': feature, 'maxResults': self.max_results}
            for feature in self.features
        ]
        return {
            'requests': [
                {
                    'image': {'content': image_content},
                    'features': feature_list,
                }
            ]
        }

    def _parse_response(self, data: dict) -> List[dict]:
        responses = data.get('responses')
        if not responses:
            return []
        response = responses[0]
        annotations = response.get('localizedObjectAnnotations') or []
        detections: List[dict] = []
        for annotation in annotations:
            try:
                name = annotation['name']
                vertices = annotation['boundingPoly']['normalizedVertices']
            except Exception:
                continue
            if not vertices:
                continue
            center_x = sum(v.get('x', 0.0) for v in vertices) / len(vertices)
            center_y = sum(v.get('y', 0.0) for v in vertices) / len(vertices)
            area = self._polygon_area(vertices)
            distance = self._estimate_distance(area)
            angle = (center_x - 0.5) * 90.0  # widen FOV to 90°
            detections.append(
                {
                    'label': name.lower().replace(' ', '_'),
                    'distance_cm': distance,
                    'angle_deg': angle,
                    'color': name.split()[0].lower(),
                    'shape': name.split()[-1].lower(),
                    'center': {'x': center_x, 'y': center_y},
                }
            )
        return detections

    @staticmethod
    def _polygon_area(vertices: List[dict]) -> float:
        if len(vertices) < 3:
            return 0.0
        area = 0.0
        for i in range(len(vertices)):
            x1 = vertices[i].get('x', 0.0)
            y1 = vertices[i].get('y', 0.0)
            x2 = vertices[(i + 1) % len(vertices)].get('x', 0.0)
            y2 = vertices[(i + 1) % len(vertices)].get('y', 0.0)
            area += x1 * y2 - x2 * y1
        return abs(area) / 2.0

    @staticmethod
    def _estimate_distance(normalized_area: float) -> float:
        # Normalised area is relative to the frame size (0..0.5 typical)
        if normalized_area <= 0:
            return 80.0
        distance = 150.0 * (normalized_area ** -0.5)
        return max(6.0, min(distance, 120.0))
