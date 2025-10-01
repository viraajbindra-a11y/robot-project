"""Camera vision helpers (optional feature)."""

from __future__ import annotations

import logging
from typing import Generator, Optional

try:  # pragma: no cover - OpenCV optional
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

LOGGER = logging.getLogger(__name__)


class CameraVision:
    def __init__(self, device: int = 0, cascade_path: Optional[str] = None, *, simulate: bool = False) -> None:
        self.device = device
        self.simulate = simulate or cv2 is None
        self.cascade_path = cascade_path or (cv2.data.haarcascades + 'haarcascade_frontalface_default.xml' if cv2 else '')
        self._capture = None
        self._classifier = None
        if not self.simulate and cv2:
            self._capture = cv2.VideoCapture(device)
            if not self._capture.isOpened():
                LOGGER.warning("Failed to open camera %s; switching to simulation", device)
                self.simulate = True
            else:
                self._classifier = cv2.CascadeClassifier(self.cascade_path)

    def frames(self) -> Generator[Optional['FrameResult'], None, None]:
        while True:
            if self.simulate:
                yield FrameResult(faces=0)
                continue
            assert cv2 and self._capture
            ret, frame = self._capture.read()
            if not ret:
                LOGGER.warning("Camera read failed")
                yield None
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self._classifier.detectMultiScale(gray, 1.3, 5) if self._classifier is not None else []
            yield FrameResult(faces=len(faces), raw_frame=frame, grayscale=gray)

    def close(self) -> None:
        if self._capture:
            self._capture.release()
        if cv2:
            cv2.destroyAllWindows()


class FrameResult:
    def __init__(self, *, faces: int, raw_frame=None, grayscale=None) -> None:
        self.faces = faces
        self.raw_frame = raw_frame
        self.grayscale = grayscale

    def __repr__(self) -> str:
        return f"FrameResult(faces={self.faces})"


def print_face_detection_loop(device: int = 0, simulate: bool = False) -> None:
    vision = CameraVision(device=device, simulate=simulate)
    try:
        for frame in vision.frames():
            if frame is None:
                continue
            LOGGER.info("Detected %s face(s)", frame.faces)
    except KeyboardInterrupt:
        LOGGER.info("Stopping camera vision loop")
    finally:
        vision.close()
