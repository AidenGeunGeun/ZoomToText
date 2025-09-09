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
            # Prefer GPU when available
            try:
                import torch  # type: ignore

                device = "cuda" if torch.cuda.is_available() else "cpu"  # pragma: no cover - env dependent
            except Exception:
                device = None  # let whisper decide

            try:
                if device:
                    self._model = whisper.load_model(self.model_name, device=device)
                else:
                    self._model = whisper.load_model(self.model_name)
            except Exception as exc:
                # Graceful compatibility: map common turbo aliases to large-v3 if unsupported
                alias = self.model_name.lower()
                if alias in {"turbo", "large-v3-turbo", "whisper-large-v3-turbo"}:
                    if device:
                        self._model = whisper.load_model("large-v3", device=device)
                    else:
                        self._model = whisper.load_model("large-v3")
                else:
                    raise

    def transcribe(self, audio_path: Path) -> List[Segment]:
        self._load()
        path_str = str(audio_path)
        # Default: let Whisper use ffmpeg/load_audio for maximum compatibility
        try:
            result_dict = self._model.transcribe(path_str)
        except Exception as exc:
            # Fallback: if ffmpeg is missing but the input is a simple 16kHz WAV
            # (as produced by our loopback capture), read samples directly.
            if path_str.lower().endswith(".wav"):
                try:
                    import wave
                    import numpy as np  # type: ignore

                    with wave.open(path_str, "rb") as wf:
                        fr = wf.getframerate()
                        ch = wf.getnchannels()
                        sw = wf.getsampwidth()
                        frames = wf.getnframes()
                        if fr == 16000 and sw == 2:
                            raw = wf.readframes(frames)
                            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                            if ch and ch > 1:
                                audio = audio.reshape(-1, ch).mean(axis=1)
                            result_dict = self._model.transcribe(audio)
                        else:
                            # Non 16kHz/16-bit WAV still needs ffmpeg
                            raise
                except Exception:
                    raise exc
            else:
                raise exc
        segments: List[Segment] = []
        for seg in result_dict["segments"]:
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


class FallbackASR(ASRModel):
    """ASR that retries low-confidence segments with a backup model."""

    def __init__(
        self,
        primary: ASRModel,
        fallback: ASRModel,
        *,
        threshold: float = 0.25,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.threshold = threshold

    def transcribe(self, audio_path: Path) -> List[Segment]:
        primary_segs = self.primary.transcribe(audio_path)
        # Quick check to avoid loading the fallback model unnecessarily
        needs_fallback = any(
            seg.confidence is not None and seg.confidence < self.threshold
            for seg in primary_segs
        )
        if not needs_fallback:
            return primary_segs

        fallback_segs = self.fallback.transcribe(audio_path)
        result: List[Segment] = []
        for seg in primary_segs:
            if seg.confidence is not None and seg.confidence < self.threshold:
                # Find fallback segment with maximum time overlap
                best = None
                best_overlap = 0.0
                for fb in fallback_segs:
                    overlap = min(seg.end, fb.end) - max(seg.start, fb.start)
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best = fb
                if best and (best.confidence or 0.0) >= (seg.confidence or 0.0):
                    result.append(best)
                else:
                    result.append(seg)
            else:
                result.append(seg)
        return result


class DummyASR(ASRModel):
    """A trivial ASR used for tests and documentation examples."""

    def __init__(self, segments: Iterable[Segment] | None = None) -> None:
        if segments is None:
            segments = [Segment(0.0, 1.0, "hello world", model="dummy")]
        self.segments = list(segments)

    def transcribe(self, audio_path: Path) -> List[Segment]:
        return self.segments
