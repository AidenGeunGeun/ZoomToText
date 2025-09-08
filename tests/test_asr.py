from pathlib import Path

from zoom_to_text.asr import DummyASR, Segment, FallbackASR


def test_fallback_replaces_low_conf_segment(tmp_path: Path):
    audio = tmp_path / "dummy.wav"
    audio.write_bytes(b"0")

    primary = DummyASR([
        Segment(0.0, 1.0, "primary", confidence=0.1, model="p"),
        Segment(1.0, 2.0, "ok", confidence=0.9, model="p"),
    ])
    backup = DummyASR([
        Segment(0.0, 1.0, "backup", confidence=0.8, model="b"),
        Segment(1.0, 2.0, "ok", confidence=0.95, model="b"),
    ])
    asr = FallbackASR(primary, backup, threshold=0.25)
    result = asr.transcribe(audio)
    assert result[0].text == "backup"
    assert result[0].model == "b"
    assert result[1].text == "ok"
