"""Audio capture utilities for ZoomToText."""
from __future__ import annotations

from pathlib import Path

try:  # pragma: no cover - optional dependency
    import sounddevice as sd
except Exception as e:  # pragma: no cover
    sd = None

import wave


def record_audio(
    duration: float,
    output_path: Path,
    samplerate: int = 16000,
    channels: int = 1,
    device: str | int | None = None,
) -> None:
    """Record audio from ``device`` for ``duration`` seconds.

    Parameters
    ----------
    duration: float
        Number of seconds to record.
    output_path: Path
        Where to save the captured WAV file.
    samplerate: int, optional
        Sampling rate to use, default ``16000``.
    channels: int, optional
        Number of audio channels, default ``1``.
    device: str | int | None, optional
        Input device name or index understood by sounddevice.
    """
    if sd is None:
        raise RuntimeError("sounddevice is required for live capture")

    frames = int(duration * samplerate)
    recording = sd.rec(frames, samplerate=samplerate, channels=channels, dtype="int16", device=device)
    sd.wait()
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit audio
        wf.setframerate(samplerate)
        wf.writeframes(recording.tobytes())


def list_devices() -> list[str]:  # pragma: no cover - passthrough
    """Return available audio input devices."""
    if sd is None:
        raise RuntimeError("sounddevice is required to list devices")
    return sd.query_devices()
