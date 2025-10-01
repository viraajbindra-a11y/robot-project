"""Voice IO helpers with speech recognition and WALL·E inspired TTS."""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence

try:  # pragma: no cover - import depends on environment
    import speech_recognition as sr  # type: ignore
except Exception:  # pragma: no cover - fall back to simulation
    sr = None  # type: ignore

try:  # pragma: no cover - import depends on environment
    import pyttsx3  # type: ignore
except Exception:  # pragma: no cover - fall back to simulation
    pyttsx3 = None  # type: ignore

if sr:  # pragma: no cover - requires speech_recognition
    UnknownValueError = sr.UnknownValueError  # type: ignore[attr-defined]
    RequestError = sr.RequestError  # type: ignore[attr-defined]
else:  # pragma: no cover - fallback for tests without speech_recognition
    class UnknownValueError(Exception):
        """Placeholder when speech_recognition is unavailable."""

    class RequestError(Exception):
        """Placeholder when speech_recognition is unavailable."""


class VoiceError(RuntimeError):
    """Raised when speech IO fails in non-simulated mode."""


class Voice:
    """Speech helper that balances real hardware with deterministic simulation."""

    def __init__(
        self,
        *,
        simulate: bool = False,
        logger: Optional[logging.Logger] = None,
        recognizer: Optional[Any] = None,
        microphone: Optional[Any] = None,
        tts_engine: Optional[Any] = None,
        recognition_method: str = "google",
        recognition_language: str = "en-US",
        auto_calibrate: bool = True,
        calibrate_duration: float = 0.5,
        voice_keyword: str = "wall",
        speech_rate: int = 140,
        speech_volume: float = 0.9,
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self.last_command: Optional[str] = None

        self._recognition_method = recognition_method
        self._recognition_language = recognition_language
        self._auto_calibrate = auto_calibrate
        self._calibrate_duration = max(0.0, calibrate_duration)
        self._voice_keyword = voice_keyword
        self._speech_rate = speech_rate
        self._speech_volume = max(0.0, min(1.0, speech_volume))

        self._recognizer: Optional[Any] = None
        self._microphone: Optional[Any] = None
        self._tts_engine: Optional[Any] = None

        self._simulate_input = simulate or (sr is None and recognizer is None)
        self._simulate_output = simulate or (pyttsx3 is None and tts_engine is None)

        if not self._simulate_input:
            if recognizer is not None:
                self._recognizer = recognizer
            elif sr:
                self._recognizer = sr.Recognizer()
            else:
                self._simulate_input = True

            if microphone is not None:
                self._microphone = microphone
            elif sr:
                try:
                    self._microphone = sr.Microphone()
                except Exception as exc:  # pragma: no cover - hardware required
                    self._logger.warning("Falling back to simulated voice input: %s", exc)
                    self._simulate_input = True
            else:
                self._simulate_input = True

        if not self._simulate_output:
            engine: Optional[Any]
            try:
                engine = tts_engine or (pyttsx3.init() if pyttsx3 else None)
            except Exception as exc:  # pragma: no cover - environment specific
                self._logger.warning("Text-to-speech initialisation failed: %s", exc)
                engine = None
            if engine is None:
                self._simulate_output = True
            else:
                self._tts_engine = engine
                self._configure_tts_engine()

        self._simulate = self._simulate_input and self._simulate_output

    @property
    def is_simulation(self) -> bool:
        """Return True when both speech directions are simulated."""
        return self._simulate

    @property
    def input_available(self) -> bool:
        """Return True when real microphone capture is active."""
        return not self._simulate_input

    @property
    def output_available(self) -> bool:
        """Return True when real TTS playback is active."""
        return not self._simulate_output

    def speak(self, message: str) -> str:
        rendered = f"Speaking: {message}"
        if self._simulate_output or not self._tts_engine:
            return rendered
        try:
            self._tts_engine.say(message)
            self._tts_engine.runAndWait()
        except Exception as exc:  # pragma: no cover - runtime failure
            self._logger.warning("Text-to-speech failed: %s", exc)
        return rendered

    def listen(
        self,
        command: Optional[str] = None,
        *,
        timeout: Optional[float] = None,
        phrase_time_limit: Optional[float] = None,
        auto_calibrate: Optional[bool] = None,
    ) -> Optional[str]:
        if command is not None:
            self.last_command = command
            return command

        if self._simulate_input:
            self.last_command = None
            return None

        if not (self._recognizer and self._microphone):
            raise VoiceError("Speech recognition is not available")

        calibrate = self._auto_calibrate if auto_calibrate is None else auto_calibrate

        with self._microphone as source:  # pragma: no cover - requires audio hardware
            if calibrate:
                try:
                    self._recognizer.adjust_for_ambient_noise(source, duration=self._calibrate_duration)
                except Exception as exc:
                    self._logger.debug("Ambient calibration skipped: %s", exc)
            audio = self._recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit,
            )

        text = self._recognise(audio)
        self.last_command = text
        return text

    def set_voice_profile(
        self,
        *,
        voice_keyword: Optional[str] = None,
        speech_rate: Optional[int] = None,
        speech_volume: Optional[float] = None,
    ) -> None:
        if voice_keyword is not None:
            self._voice_keyword = voice_keyword
        if speech_rate is not None:
            self._speech_rate = speech_rate
        if speech_volume is not None:
            self._speech_volume = max(0.0, min(1.0, speech_volume))
        if self._tts_engine:
            self._configure_tts_engine()

    def _configure_tts_engine(self) -> None:
        assert self._tts_engine is not None
        try:
            self._tts_engine.setProperty('rate', self._speech_rate)
        except Exception:  # pragma: no cover - engine specific
            self._logger.debug("TTS engine did not accept rate setting")
        try:
            self._tts_engine.setProperty('volume', self._speech_volume)
        except Exception:  # pragma: no cover - engine specific
            self._logger.debug("TTS engine did not accept volume setting")

        voice_id = self._select_voice(self._voice_keyword)
        if voice_id:
            try:
                self._tts_engine.setProperty('voice', voice_id)
            except Exception:  # pragma: no cover - engine specific
                self._logger.debug("Voice id %s not supported", voice_id)

    def _select_voice(self, keyword: str) -> Optional[str]:
        if not self._tts_engine:
            return None
        try:
            voices: Optional[Sequence[Any]] = self._tts_engine.getProperty('voices')
        except Exception:  # pragma: no cover - engine specific
            return None
        if not voices:
            return None

        keyword_lower = (keyword or '').lower()

        for voice in voices:
            name = getattr(voice, 'name', '')
            if keyword_lower and keyword_lower in name.lower():
                return getattr(voice, 'id', None)

        for voice in voices:
            name = getattr(voice, 'name', '').lower()
            if any(token in name for token in ('robot', 'wall', 'walle')):
                return getattr(voice, 'id', None)

        for voice in voices:
            languages = getattr(voice, 'languages', []) or []
            if any('en' in str(lang).lower() for lang in languages):
                return getattr(voice, 'id', None)

        return getattr(voices[0], 'id', None)

    def _recognise(self, audio):  # pragma: no cover - exercised with real audio only
        if self._recognizer is None:
            raise VoiceError("Speech recognizer not initialised")
        method = self._recognition_method.lower()
        try:
            if method == "google":
                recognise = getattr(self._recognizer, 'recognize_google', None)
                if recognise is None:
                    raise VoiceError("Recognizer does not support Google recognition")
                return recognise(audio, language=self._recognition_language)
            if method == "sphinx":
                recognise = getattr(self._recognizer, 'recognize_sphinx', None)
                if recognise is None:
                    raise VoiceError("Recognizer does not support Sphinx recognition")
                return recognise(audio, language=self._recognition_language)
            raise VoiceError(f"Unknown recognition method: {method}")
        except UnknownValueError:
            return None
        except RequestError as exc:
            raise VoiceError(f"Speech recognition request failed: {exc}") from exc
