from pathlib import Path

from zoom_to_text.asr import DummyASR, Segment
from zoom_to_text.pipeline import process_audio
from zoom_to_text.summarizer import DummySummarizer


def test_process_audio(tmp_path: Path):
    audio = tmp_path / "dummy.wav"
    audio.write_bytes(b"0")  # placeholder; DummyASR ignores content

    segments = [
        Segment(start=0.0, end=1.0, text="hello"),
        Segment(start=1.0, end=2.0, text="world"),
    ]
    asr = DummyASR(segments)
    summarizer = DummySummarizer()

    transcript_path, summary_path = process_audio(audio, asr, summarizer, tmp_path)
    assert transcript_path.read_text() == "[00000.00] hello\n[00001.00] world"
    assert summary_path.read_text() == "[00000.00] hello"
