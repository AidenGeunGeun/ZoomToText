"""High level pipeline for ASR-only processing (file or live)."""

from __future__ import annotations
from datetime import timedelta, datetime
from pathlib import Path
from typing import Iterable, List, Optional
import json
from .asr import ASRModel, Segment

# @TODO-5 — Add Summarizer import
from .summarizer import Summarizer


def format_transcript(segments: Iterable[Segment], *, low_conf_threshold: float = 0.25) -> str:
    lines = []
    for seg in segments:
        timestamp = str(timedelta(seconds=int(seg.start))).rjust(8, "0")
        text = seg.text.strip()
        if seg.confidence is not None and seg.confidence < low_conf_threshold:
            text += " [LOW CONFIDENCE]"
        lines.append(f"[{timestamp}] {text}")
    return "\n".join(lines)


def process_audio(
    input_path: Path,
    asr: ASRModel,
    output_dir: Path,
    # @TODO-6 — Add summarizer parameter
    summarizer: Optional[Summarizer] = None,
) -> tuple[Path, Path, Optional[Path]]:
    """Process ``input_path`` and write transcript and segments metadata.

    Returns a tuple ``(transcript_path, metadata_path, summary_path)``.
    ``summary_path`` is None if no summarizer is provided.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    segments: List[Segment] = asr.transcribe(input_path)
    transcript = format_transcript(segments)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    transcript_path = output_dir / f"transcript-{ts}.txt"
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
    metadata_path = output_dir / f"segments-{ts}.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    # @TODO-7 — Generate summary if summarizer provided
    summary_path: Optional[Path] = None
    if summarizer is not None:
        summary_text = summarizer.summarize(transcript)
        summary_path = output_dir / f"summary-{ts}.txt"
        summary_path.write_text(summary_text, encoding="utf-8")
    return transcript_path, metadata_path, summary_path
