"""System audio capture using soundcard (Windows).

This module intentionally supports only loopback capture of the active
speaker device(s). Microphone capture and other backends are out of scope
for the simplified MVP.
"""
from __future__ import annotations

from pathlib import Path
import wave

try:  # pragma: no cover - optional at import time
    import soundcard as sc  # type: ignore
except Exception:  # pragma: no cover
    sc = None


def list_loopback_speakers() -> list[dict]:  # pragma: no cover - passthrough
    """Return simplified speaker list for loopback capture via soundcard.

    Each entry is a dict: {"index": int, "name": str}.
    """
    if sc is None:
        raise RuntimeError(
            "soundcard is required. Install with 'pip install soundcard' or via project extras."
        )
    speakers = sc.all_speakers()  # type: ignore[attr-defined]
    return [{"index": i, "name": s.name} for i, s in enumerate(speakers)]


def record_until_stop_soundcard(
    output_path: Path,
    samplerate: int = 48000,
    channels: int = 2,
    device: str | int | None = None,
) -> None:
    """Record system audio using the 'soundcard' library until Ctrl+C.

    - device may be a speaker index (from list_loopback_speakers()) or a
      substring of the speaker name; when omitted, the default speaker is used.
    - Audio is saved as 16-bit PCM WAV at ``samplerate`` with ``channels``.
    """
    if sc is None:
        raise RuntimeError(
            "soundcard is not installed. Install with 'pip install soundcard' to enable loopback."
        )
    import numpy as np  # lazy import inside function

    speakers = sc.all_speakers()  # type: ignore[attr-defined]

    # Resolve speaker from index or name
    speaker = None
    if isinstance(device, int):
        try:
            speaker = speakers[device]
        except Exception as exc:  # pragma: no cover - parameter guard
            raise RuntimeError(f"Invalid speaker index {device}: {exc}")
    elif isinstance(device, str) and device:
        for sp in speakers:
            if device.lower() in (sp.name or "").lower():
                speaker = sp
                break
    if speaker is None:
        speaker = sc.default_speaker()  # type: ignore[attr-defined]

    # Use loopback microphone associated with the selected speaker
    loopback_mic = sc.get_microphone(speaker.name, include_loopback=True)  # type: ignore[attr-defined]

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit samples
        wf.setframerate(samplerate)

        # Suppress benign discontinuity warnings from Media Foundation backend
        import warnings
        try:  # type: ignore[attr-defined]
            warnings.filterwarnings(
                "ignore",
                category=sc.SoundcardRuntimeWarning,  # type: ignore[attr-defined]
                message="data discontinuity in recording",
            )
        except Exception:
            pass

        with loopback_mic.recorder(samplerate=samplerate, channels=channels) as rec:  # type: ignore[attr-defined]
            print("Recording (system audio)... Press Ctrl+C to stop.")
            try:
                while True:
                    # Use a chunk size aligned to 48 kHz clock (~10 ms)
                    chunk = 4800 if samplerate == 48000 else 2048
                    data = rec.record(chunk)
                    # Convert float32 [-1,1] to int16 PCM (stereo by default)
                    data = np.clip(data, -1.0, 1.0)
                    pcm = (data * 32767.0).astype(np.int16).tobytes()
                    wf.writeframes(pcm)
            except KeyboardInterrupt:
                print("\nStopped recording.")
