"""High level pipeline combining ASR and summarization."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Iterable, List
import json

from .asr import ASRModel, Segment
from .summarizer import Summarizer


def format_transcript(
    segments: Iterable[Segment], *, low_conf_threshold: float = 0.25
) -> str:
    lines = []
    for seg in segments:
        timestamp = str(timedelta(seconds=int(seg.start))).rjust(8, "0")
        text = seg.text.strip()
        if (
            seg.confidence is not None
            and seg.confidence < low_conf_threshold
        ):
            text += " [LOW CONFIDENCE]"
        lines.append(f"[{timestamp}] {text}")
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
    segments: List[Segment] = asr.transcribe(input_path)
    transcript = format_transcript(segments)
    transcript_path = output_dir / "transcript.txt"
    transcript_path.write_text(transcript, encoding="utf-8")

    metadata = [
        {
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
            "confidence": seg.confidence,
            "model": seg.model,
        }
        for seg in segments
    ]
    metadata_path = output_dir / "segments.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    summary_text = summarizer.summarize(transcript)
    summary_path = output_dir / "summary.md"
    summary_path.write_text(summary_text, encoding="utf-8")
    return transcript_path, summary_path
