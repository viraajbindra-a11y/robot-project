"""Local object detection using Ultralytics YOLO models.

This optional module lets the robot recognise arbitrary objects without an API
key. It relies on the ``ultralytics`` package (YOLOv8) and OpenCV to capture
frames from the Pi camera. When available, detections are converted into the
same format used by :class:`src.object_perception.ObjectRecognizer` so the
master loop can narrate results exactly like the cloud integrations.
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional

try:  # pragma: no cover - optional runtime dependency
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

try:  # pragma: no cover - optional runtime dependency
    from ultralytics import YOLO
except Exception:  # pragma: no cover
    YOLO = None  # type: ignore

LOGGER = logging.getLogger(__name__)


class LocalYoloClient:
    """Capture frames locally and run them through a YOLO model."""

    def __init__(
        self,
        *,
        model_path: str = 'yolov8n.pt',
        camera_index: int = 0,
        classes: Optional[Iterable[int]] = None,
        conf: float = 0.25,
    ) -> None:
        if YOLO is None or cv2 is None:
            raise RuntimeError(
                'LocalYoloClient requires opencv-python and ultralytics installed. '
                'Install with `pip install opencv-python ultralytics`.'
            )
        self.model = YOLO(model_path)
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError(f'Failed to open camera index {camera_index}')
        self.classes = tuple(classes) if classes is not None else None
        self.conf = conf

    def detect(self) -> List[dict]:
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError('Failed to capture frame from camera')
        height, width = frame.shape[:2]
        results = self.model(frame, stream=True, verbose=False, conf=self.conf, classes=self.classes)
        detections: List[dict] = []
        for result in results:
            names = result.names
            for box in getattr(result, 'boxes', []):
                cls_index = int(box.cls[0]) if box.cls is not None else None
                if cls_index is None:
                    continue
                label = names.get(cls_index, str(cls_index)).lower().replace(' ', '_')
                conf = float(box.conf[0]) if box.conf is not None else 0.0
                if conf <= 0:
                    continue
                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = xyxy
                center_x = ((x1 + x2) / 2.0) / max(width, 1)
                center_y = ((y1 + y2) / 2.0) / max(height, 1)
                area = max((x2 - x1) * (y2 - y1), 1.0)
                norm_area = area / float(width * height)
                detections.append(
                    {
                        'label': label,
                        'distance_cm': self._estimate_distance(norm_area),
                        'angle_deg': (center_x - 0.5) * 90.0,
                        'confidence': conf,
                        'center': {'x': float(center_x), 'y': float(center_y)},
                    }
                )
        return detections

    def close(self) -> None:
        if self.cap:
            self.cap.release()

    @staticmethod
    def _estimate_distance(normalized_area: float) -> float:
        if normalized_area <= 0:
            return 80.0
        distance = 180.0 * (normalized_area ** -0.5)
        return max(6.0, min(distance, 120.0))
