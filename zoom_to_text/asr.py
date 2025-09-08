"""ASR module for ZoomToText.

Provides an abstract base class :class:`ASRModel` and concrete implementations
for Whisper based transcription.  A lightweight :class:`DummyASR` is included
for testing purposes.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass
class Segment:
    """Represents a transcription segment."""
    start: float
    end: float
    text: str

    confidence: float | None = None
    model: str | None = None

class ASRModel:
    """Abstract base class for ASR engines."""

    def transcribe(self, audio_path: Path) -> List[Segment]:
        """Transcribe ``audio_path`` and return a list of segments."""
        raise NotImplementedError


class WhisperASR(ASRModel):
    """ASR implementation backed by OpenAI's Whisper models."""

    def __init__(self, model_name: str = "small") -> None:
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                import whisper  # Lazy import so tests don't require the package
            except ModuleNotFoundError as exc:  # pragma: no cover - import guard
                raise RuntimeError(
                    "WhisperASR requires the 'openai-whisper' package. Install with"
                    " `pip install .[whisper]`."
                ) from exc

            self._model = whisper.load_model(self.model_name)

    def transcribe(self, audio_path: Path) -> List[Segment]:
        self._load()
        result = self._model.transcribe(str(audio_path))
        segments: List[Segment] = []
        for seg in result["segments"]:
            conf = None
            if "avg_logprob" in seg:
                import math

                conf = math.exp(seg["avg_logprob"])
            segments.append(
                Segment(
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"].strip(),
                    confidence=conf,
                    model=self.model_name,
                )
            )
        return segments


class DummyASR(ASRModel):
    """A trivial ASR used for tests and documentation examples."""
    def __init__(self, segments: Iterable[Segment] | None = None) -> None:
        if segments is None:
            segments = [Segment(0.0, 1.0, "hello world", model="dummy")]
