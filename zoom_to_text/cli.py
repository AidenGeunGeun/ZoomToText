"""Command line interface for ZoomToText."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import tempfile

import typer

from .asr import DummyASR, WhisperASR
from .pipeline import process_audio
from .summarizer import DummySummarizer, OpenAISummarizer, GeminiSummarizer
from .capture import record_audio, list_devices

app = typer.Typer(add_completion=False)


def _resolve_asr(model: str) -> WhisperASR | DummyASR:
    if model == "dummy":
        return DummyASR()
    return WhisperASR(model_name=model)


def _resolve_summarizer(
    provider: str, api_key: Optional[str], model: str
) -> OpenAISummarizer | GeminiSummarizer | DummySummarizer:
    if provider == "gemini":
        if model == "gpt-3.5-turbo":
            model = "gemini-pro"
        if api_key:
            return GeminiSummarizer(api_key=api_key, model=model)
    if provider == "openai" and api_key:
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
    summary_provider: str = typer.Option(
        "openai", help="Summarization backend: openai, gemini, dummy"
    ),
    summary_model: str = typer.Option("gpt-3.5-turbo"),
    api_key: Optional[str] = typer.Option(
        None, envvar=["OPENAI_API_KEY", "GEMINI_API_KEY"], help="API key for summarizer"
    ),
    list_devices_flag: bool = typer.Option(
        False, "--list-devices", help="List audio capture devices and exit"
    ),
) -> None:
    """Transcribe an audio/video file or live capture and produce transcript and summary."""

    if list_devices_flag:
        try:
            for i, dev in enumerate(list_devices()):
                typer.echo(f"{i}: {dev}")
        except Exception as exc:  # pragma: no cover - depends on sounddevice
            raise typer.Exit(str(exc))
        raise typer.Exit()

    if not live and input_path is None:
        raise typer.BadParameter("--input is required when not using --live")

    temp_path: Optional[Path] = None
    try:
        if live:
            if duration <= 0:
                raise typer.BadParameter("--duration must be greater than zero for live capture")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                temp_path = Path(tmp.name)
            try:
                record_audio(duration, temp_path, device=device)
            except RuntimeError as exc:
                raise typer.BadParameter(str(exc))
            input_path = temp_path

        asr = _resolve_asr(asr_model)
        summarizer = _resolve_summarizer(summary_provider, api_key, summary_model)
        process_audio(input_path, asr, summarizer, output_dir)
        typer.echo(f"Transcript and summary written to {output_dir}")
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":  # pragma: no cover
    app()
