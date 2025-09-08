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
            "--summary-provider",
            "dummy",
        ],
    )
    assert result.exit_code == 0, result.stdout
    transcript = (tmp_path / "transcript.txt").read_text()
    assert "[LOW CONFIDENCE]" in transcript
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "segments.json").exists()
