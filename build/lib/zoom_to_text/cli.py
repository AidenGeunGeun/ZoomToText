"""Command line interface for ZoomToText (ASR-only)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import tempfile

import typer

from .asr import ASRModel, DummyASR, WhisperASR
from .pipeline import process_audio
from .capture import record_until_stop, list_output_devices, list_devices

app = typer.Typer(add_completion=False)


def _resolve_asr(model: str) -> ASRModel:
    primary: ASRModel
    if model == "dummy":
        primary = DummyASR()
    else:
        primary = WhisperASR(model_name=model)
    return primary


 # Summarization removed in ASR-only mode


@app.command()
def transcribe(
    input_path: Optional[Path] = typer.Option(
        None, "--input", "-i", exists=True, readable=True, help="Audio or video file to transcribe."
    ),
    live: bool = typer.Option(False, help="Capture live audio instead of reading from file."),
    device: Optional[str] = typer.Option(None, help="Device index or name for capture."),
    loopback: bool = typer.Option(
        False,
        help="Capture system audio (WASAPI loopback on Windows). Use with --device from --list-devices.",
    ),
    output_dir: Path = typer.Option(Path("output")),
    asr_model: str = typer.Option("small", help="Primary Whisper model name or 'dummy'."),
    list_devices_flag: bool = typer.Option(
        False, "--list-devices", help="List audio capture devices and exit"
    ),
) -> None:
    """Transcribe an audio/video file or live capture and write transcript + segments."""

    if list_devices_flag:
        try:
            outputs = list_output_devices(loopback_only=True)
        except Exception as exc:  # pragma: no cover - depends on sounddevice
            raise typer.Exit(str(exc))
        if not outputs:
            typer.echo("No WASAPI output devices found.")
            # Try listing soundcard speakers as a fallback hint
            try:
                import soundcard as sc  # type: ignore

                speakers = sc.all_speakers()
                if speakers:
                    typer.echo("Available speakers (soundcard):")
                    for i, sp in enumerate(speakers):
                        typer.echo(f"  {i}: {sp.name}")
                    typer.echo(
                        "\nInstall loopback support with 'pip install .[loopback]' and run:\n"
                        "  python -m zoom_to_text.cli --live --loopback --device <speaker name or index>"
                    )
                else:
                    typer.echo(
                        "Alternatively enable 'Stereo Mix' in Windows Recording devices and capture it with --device."
                    )
            except Exception:
                typer.echo(
                    "Install loopback support with 'pip install .[loopback]' to capture system audio,"
                    " or enable 'Stereo Mix' in Windows Sound settings."
                )
        else:
            typer.echo("Loopback-capable outputs (WASAPI):")
            for dev in outputs:
                idx = dev["index"]
                name = dev["name"]
                typer.echo(f"  {idx}: {name}")
            typer.echo(
                "\nExample (system audio):\n"
                "  python -m zoom_to_text.cli --live --loopback --device <index>\n"
                "Press Ctrl+C to stop."
            )
        raise typer.Exit()

    if not live and input_path is None:
        raise typer.BadParameter("--input is required when not using --live")

    temp_path: Optional[Path] = None
    try:
        if live:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                temp_path = Path(tmp.name)
            try:
                # Live capture runs until user stops (Ctrl+C on Windows)
                resolved_device: int | str | None
                if device is None:
                    resolved_device = None
                else:
                    resolved_device = int(device) if device.isdigit() else device
                try:
                    record_until_stop(temp_path, device=resolved_device, loopback=loopback)
                except RuntimeError as exc:
                    if loopback:
                        # Fallback to soundcard-based loopback if available
                        try:
                            from .capture import record_until_stop_soundcard

                            # Try to preserve device selection if a name was provided
                            dev_name = None if resolved_device is None or isinstance(resolved_device, int) else resolved_device
                            record_until_stop_soundcard(temp_path, device_name=dev_name)
                        except Exception as exc2:  # pragma: no cover - env dependent
                            raise typer.BadParameter(
                                f"Loopback not available via sounddevice ({exc}). Install 'soundcard' with 'pip install .[loopback]' and try again: {exc2}"
                            )
                    else:
                        raise
            except RuntimeError as exc:
                raise typer.BadParameter(str(exc))
            input_path = temp_path

        asr = _resolve_asr(asr_model)
        process_audio(input_path, asr, output_dir)
        typer.echo(f"Transcript and segments written to {output_dir}")
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":  # pragma: no cover
    app()
