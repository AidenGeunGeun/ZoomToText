from pathlib import Path

from zoom_to_text.asr import DummyASR, Segment
from zoom_to_text.pipeline import process_audio
import json


def test_process_audio(tmp_path: Path):
    audio = tmp_path / "dummy.wav"
    audio.write_bytes(b"0")  # placeholder; DummyASR ignores content

    segments = [
        Segment(start=0.0, end=1.0, text="hello", confidence=0.9),
        Segment(start=1.0, end=2.0, text="world", confidence=0.1),
    ]
    asr = DummyASR(segments)
    transcript_path, metadata_path = process_audio(audio, asr, tmp_path)
    assert (
        transcript_path.read_text()
        == "[00:00:00] hello\n[00:00:01] world [LOW CONFIDENCE]"
    )
    metadata = json.loads(metadata_path.read_text())
    assert metadata[1]["confidence"] == 0.1
    assert metadata[1]["model"] is None
