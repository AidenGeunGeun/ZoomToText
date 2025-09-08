"""Command line interface for ZoomToText."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import tempfile

import typer

from .asr import DummyASR, WhisperASR
from .pipeline import process_audio
from .summarizer import DummySummarizer, OpenAISummarizer
from .capture import record_audio

app = typer.Typer(add_completion=False)


def _resolve_asr(model: str) -> WhisperASR | DummyASR:
    if model == "dummy":
        return DummyASR()
    return WhisperASR(model_name=model)


def _resolve_summarizer(api_key: Optional[str], model: str) -> OpenAISummarizer | DummySummarizer:
    if api_key:
        return OpenAISummarizer(api_key=api_key, model=model)
    return DummySummarizer()


@app.command()
def transcribe(
    input_path: Optional[Path] = typer.Option(
        None, "--input", "-i", exists=True, readable=True, help="Audio or video file to transcribe."
    ),
    live: bool = typer.Option(False, help="Capture live audio instead of reading from file."),
    duration: float = typer.Option(0.0, help="Duration in seconds for live capture."),
    device: Optional[str] = typer.Option(None, help="Input device for live capture."),
    output_dir: Path = typer.Option(Path("output")),
    asr_model: str = typer.Option("small", help="Whisper model name or 'dummy'."),
    summary_model: str = typer.Option("gpt-3.5-turbo"),
    api_key: Optional[str] = typer.Option(None, envvar="OPENAI_API_KEY"),
) -> None:
    """Transcribe an audio/video file or live capture and produce transcript and summary."""

    if not live and input_path is None:
        raise typer.BadParameter("--input is required when not using --live")

    temp_path: Optional[Path] = None
    if live:
        if duration <= 0:
            raise typer.BadParameter("--duration must be greater than zero for live capture")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            temp_path = Path(tmp.name)
        record_audio(duration, temp_path, device=device)
        input_path = temp_path

    asr = _resolve_asr(asr_model)
    summarizer = _resolve_summarizer(api_key, summary_model)
    process_audio(input_path, asr, summarizer, output_dir)
    typer.echo(f"Transcript and summary written to {output_dir}")

    if temp_path is not None:
        temp_path.unlink(missing_ok=True)


if __name__ == "__main__":  # pragma: no cover
    app()
