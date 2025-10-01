"""Client helper for calling a remote vision inference API."""

from __future__ import annotations

import base64
import logging
from typing import Dict, List, Optional

try:  # pragma: no cover - optional dependency
    import cv2
    import requests
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore
    requests = None  # type: ignore

LOGGER = logging.getLogger(__name__)


class RemoteVisionClient:
    """Capture frames from the Pi camera and send them to a vision API."""

    def __init__(self, api_url: str, api_key: str, camera_index: int = 0) -> None:
        if cv2 is None or requests is None:
            raise RuntimeError("remote_vision requires opencv-python and requests installed")
        self.api_url = api_url
        self.api_key = api_key
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera index {camera_index}")

    def snapshot_jpeg(self) -> bytes:
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("Failed to capture frame from camera")
        ok, buffer = cv2.imencode('.jpg', frame)
        if not ok:
            raise RuntimeError("Failed to encode frame to JPEG")
        return buffer.tobytes()

    def detect(self) -> List[Dict]:
        frame_bytes = self.snapshot_jpeg()
        payload = {
            'image_base64': base64.b64encode(frame_bytes).decode('utf-8'),
        }
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        resp = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get('detections', [])

    def close(self) -> None:
        if self.cap:
            self.cap.release()
