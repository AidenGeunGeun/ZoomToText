"""Audio capture utilities for ZoomToText."""
from __future__ import annotations

from pathlib import Path
import sys
import queue

try:  # pragma: no cover - optional dependency
    import sounddevice as sd
except Exception:  # pragma: no cover
    sd = None

import wave
try:  # optional loopback fallback
    import soundcard as sc  # type: ignore
except Exception:  # pragma: no cover
    sc = None


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

def record_until_stop(
    output_path: Path,
    samplerate: int = 16000,
    channels: int = 1,
    device: str | int | None = None,
    *,
    loopback: bool = False,
) -> None:
    """Continuously record until the user stops (Ctrl+C on Windows).

    When ``loopback=True`` on Windows, captures system audio from a WASAPI
    output device ("What You Hear"). ``device`` must refer to an output device
    from the WASAPI host API in that case.
    """
    if sd is None:
        raise RuntimeError("sounddevice is required for live capture")

    q: "queue.Queue[bytes]" = queue.Queue()

    def callback(indata, frames, time, status):  # pragma: no cover - real-time callback
        if status:
            print(status, file=sys.stderr)
        q.put(bytes(indata))

    # Resolve channels for loopback (prefer stereo when available)
    use_channels = channels
    extra_settings = None
    if loopback:
        try:
            hostapis = sd.query_hostapis()
            # Find WASAPI host API id robustly
            wasapi_id = next(
                (i for i, h in enumerate(hostapis) if "WASAPI" in h.get("name", "").upper()),
                None,
            )
        except Exception:
            wasapi_id = None

        if wasapi_id is None:
            raise RuntimeError(
                "Loopback capture requires Windows WASAPI. No WASAPI host API found."
            )
        if device is None:
            raise RuntimeError(
                "Loopback capture needs a specific output device index. Run with --list-devices to choose one."
            )
        try:
            dev_info = sd.query_devices(device)
        except Exception as exc:
            raise RuntimeError(f"Invalid device {device!r} for loopback: {exc}")
        if dev_info.get("hostapi") != wasapi_id or dev_info.get("max_output_channels", 0) <= 0:
            raise RuntimeError(
                "Selected device is not a WASAPI output device. Use an index from --list-devices."
            )
        # Prefer 2 channels if the output supports it
        if dev_info.get("max_output_channels", 0) >= 2 and channels < 2:
            use_channels = 2
        elif dev_info.get("max_output_channels", 0) < channels:
            use_channels = max(1, int(dev_info.get("max_output_channels", 1)))

        try:  # pragma: no cover - Windows-specific
            extra_settings = sd.WasapiSettings(loopback=True)
        except Exception as exc:
            raise RuntimeError(
                "Your sounddevice build does not support WASAPI loopback."
            ) from exc

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(use_channels)
        wf.setsampwidth(2)  # 16-bit audio
        wf.setframerate(samplerate)

        with sd.InputStream(
            samplerate=samplerate,
            channels=use_channels,
            dtype="int16",
            device=device,
            callback=callback,
            extra_settings=extra_settings,  # type: ignore[arg-type]
        ):
            print("Recording... Press Ctrl+C to stop.")
            try:
                while True:
                    wf.writeframes(q.get())
            except KeyboardInterrupt:
                print("\nStopped recording.")

def list_devices() -> list:  # pragma: no cover - passthrough
    """Return available audio devices (raw from sounddevice)."""
    if sd is None:
        raise RuntimeError("sounddevice is required to list devices")
    return sd.query_devices()


def list_output_devices(loopback_only: bool = True) -> list[dict]:  # pragma: no cover - passthrough
    """Return simplified info for output devices.

    When ``loopback_only`` is True, only return WASAPI output devices that can
    be used for loopback capture on Windows.
    """
    if sd is None:
        raise RuntimeError("sounddevice is required to list devices")
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    # Map hostapi id -> name
    hostapi_names = {i: h.get("name", str(i)) for i, h in enumerate(hostapis)}
    wasapi_id = next((i for i, n in hostapi_names.items() if "WASAPI" in n.upper()), None)

    result: list[dict] = []
    if loopback_only and wasapi_id is None:
        return []

    for idx, dev in enumerate(devices):
        if dev.get("max_output_channels", 0) <= 0:
            continue
        if loopback_only and wasapi_id is not None and dev.get("hostapi") != wasapi_id:
            continue
        result.append(
            {
                "index": idx,
                "name": dev.get("name"),
                "hostapi": hostapi_names.get(dev.get("hostapi"), str(dev.get("hostapi"))),
                "channels": dev.get("max_output_channels", 0),
                "samplerate": dev.get("default_samplerate"),
            }
        )
    return result


def record_until_stop_soundcard(
    output_path: Path,
    samplerate: int = 16000,
    channels: int = 2,
    device_name: str | None = None,
) -> None:
    """Record system audio using the 'soundcard' library until Ctrl+C.

    Captures from the default speaker or a named speaker. Requires the optional
    dependency 'soundcard' (install with the 'loopback' extra).
    """
    if sc is None:
        raise RuntimeError(
            "soundcard is not installed. Install with 'pip install .[loopback]' or 'pip install soundcard'."
        )
    import numpy as np  # lazy import

    # Pick speaker
    speaker = None
    if device_name:
        for sp in sc.all_speakers():  # type: ignore[attr-defined]
            if device_name.lower() in (sp.name or "").lower():
                speaker = sp
                break
    if speaker is None:
        speaker = sc.default_speaker()  # type: ignore[attr-defined]

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)

        with speaker.recorder(samplerate=samplerate, channels=channels) as rec:  # type: ignore[attr-defined]
            print("Recording (soundcard loopback)... Press Ctrl+C to stop.")
            try:
                while True:
                    data = rec.record(2048)
                    # Convert float32 [-1,1] to int16 PCM
                    data = np.clip(data, -1.0, 1.0)
                    pcm = (data * 32767.0).astype(np.int16).tobytes()
                    wf.writeframes(pcm)
            except KeyboardInterrupt:
                print("\nStopped recording.")
