"""High level pipeline combining ASR and summarization."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .asr import ASRModel, Segment
from .summarizer import Summarizer


def format_transcript(segments: Iterable[Segment]) -> str:
    lines = [
        f"[{seg.start:08.2f}] {seg.text.strip()}" for seg in segments
    ]
    return "\n".join(lines)


def process_audio(
    input_path: Path,
    asr: ASRModel,
    summarizer: Summarizer,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Process ``input_path`` and write transcript and summary files.

    Returns a tuple of paths ``(transcript_path, summary_path)``.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    segments = asr.transcribe(input_path)
    transcript = format_transcript(segments)
    transcript_path = output_dir / "transcript.txt"
    transcript_path.write_text(transcript, encoding="utf-8")

    summary_text = summarizer.summarize(transcript)
    summary_path = output_dir / "summary.md"
    summary_path.write_text(summary_text, encoding="utf-8")
    return transcript_path, summary_path
