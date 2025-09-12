"""Command line interface for ZoomToText (ASR-only)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import tempfile

import typer

from .asr import ASRModel, DummyASR, WhisperASR
from .pipeline import process_audio
from .capture import record_until_stop_soundcard, list_loopback_speakers

app = typer.Typer(add_completion=False)


def _resolve_asr(model: str) -> ASRModel:
    primary: ASRModel
    if model == "dummy":
        primary = DummyASR()
    else:
        primary = WhisperASR(model_name=model)
    return primary


 # Summarization removed in ASR-only mode


@app.callback(invoke_without_command=True)
def main(
    input_path: Optional[Path] = typer.Option(
        None, "--input", "-i", exists=True, readable=True, help="Audio or video file to transcribe."
    ),
    live: bool = typer.Option(False, help="Capture system audio (loopback) instead of reading from file."),
    device: Optional[str] = typer.Option(None, help="Speaker index (preferred) or name substring for loopback capture."),
    output_dir: Path = typer.Option(
        Path("output"),
        "--output",
        "--output-dir",
        help="Directory to write transcript and segments (default: ./output)",
    ),
    asr_model: str = typer.Option(
        "turbo",
        help="ASR model name: e.g., 'turbo' (default), 'large-v3', 'small', or 'dummy'.",
    ),
    list_devices_flag: bool = typer.Option(False, "--list-devices", help="List loopback speakers and exit"),
) -> None:
    """Transcribe an audio/video file or live capture and write transcript + segments."""

    if list_devices_flag:
        try:
            speakers = list_loopback_speakers()
        except Exception as exc:  # pragma: no cover - env dependent
            typer.echo(str(exc))
            raise typer.Exit(1)
        typer.echo("Speakers (loopback via soundcard):")
        for sp in speakers:
            typer.echo(f"  {sp['index']}: {sp['name']}")
        typer.echo(
            "\nExample (system audio):\n"
            "  python -m zoom_to_text.cli --live --device <index>\n"
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
                # Live capture (system audio only) runs until user stops (Ctrl+C)
                resolved_device: int | str | None
                if device is None:
                    resolved_device = None
                else:
                    resolved_device = int(device) if device.isdigit() else device
                record_until_stop_soundcard(temp_path, device=resolved_device)
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
