from pathlib import Path
from typer.testing import CliRunner

from zoom_to_text.cli import app
from zoom_to_text.asr import Segment

runner = CliRunner()


def test_cli_requires_input():
    result = runner.invoke(app, ["transcribe"])
    assert result.exit_code != 0


def test_cli_file_transcription(tmp_path: Path, monkeypatch):
    class LowConfDummy:
        def __init__(self):
            self.segments = [Segment(0.0, 1.0, "hello", confidence=0.1)]

        def transcribe(self, audio_path: Path):
            return self.segments

    monkeypatch.setattr("zoom_to_text.cli.DummyASR", LowConfDummy)

    audio = tmp_path / "dummy.wav"
    audio.write_bytes(b"0")
    result = runner.invoke(
        app,
        [
            "transcribe",
            "--input",
            str(audio),
            "--output",
            str(tmp_path),
            "--asr-model",
            "dummy",
        ],
    )
    assert result.exit_code == 0, result.stdout
    transcripts = sorted(tmp_path.glob("transcript-*.txt"))
    assert transcripts, "No transcript-* file written"
    transcript = transcripts[-1].read_text()
    assert "[LOW CONFIDENCE]" in transcript
    segments = sorted(tmp_path.glob("segments-*.json"))
    assert segments, "No segments-* file written"
