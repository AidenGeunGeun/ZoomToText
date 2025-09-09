# ZoomToText

Windows‑native CLI that performs local Whisper ASR on audio from a file or from system audio (loopback). It writes a timestamped transcript and segment metadata locally. No cloud features.

## Features
- Local Whisper ASR (GPU preferred; CPU supported)
- Live system‑audio capture (loopback) or file input
- Simple device selection (`--list-devices`, `--device <index>`) on Windows
- Timestamped outputs to avoid overwrites

## Requirements
- Windows 10/11
- Python 3.10+
- FFmpeg on PATH for non‑WAV inputs (recommended)

## Install

Option A — bootstrap script (recommended):

1) Open PowerShell in the repo folder
2) Run:

```
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -Torch cpu -InstallFFmpeg
```

- Creates `.venv`, upgrades pip, installs `soundcard` (loopback), PyTorch (CPU), Whisper, and FFmpeg (via winget/choco when available).
- For NVIDIA GPU, use `-Torch cu121` or `-Torch cu122` or whatever CUDA version you're running, instead of `cpu`.

Option B — manual steps (use a virtual environment):

```
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install soundcard
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
python -m pip install .[whisper]
```

Notes:
- Always install inside your virtual environment.
- To support formats like mp3/m4a/mp4, install FFmpeg (e.g., `winget install -e --id Gyan.FFmpeg`).
- Loopback capture uses `soundcard` and works on common Windows setups without extra config.

## Usage

List devices (loopback speakers):

```
python -m zoom_to_text.cli --list-devices
```

Transcribe a file:

```
python -m zoom_to_text.cli transcribe --input input.wav --output-dir outdir
```

Capture system audio (live) until Ctrl+C:

```
python -m zoom_to_text.cli --live --device <index> --output-dir outdir
```

Model selection:
- Default is `--asr-model turbo`; if unavailable, falls back to `large-v3` automatically.
- You can choose other Whisper models (e.g., `small`, `base`, `large-v3`) or `dummy` for tests.

Outputs (no overwrites):
- `transcript-YYYYMMDD-HHMMSS.txt`
- `segments-YYYYMMDD-HHMMSS.json`

Tip: `--output-dir` also has an alias `--output`.

## Troubleshooting
- FFmpeg missing: If non‑WAV inputs fail, install FFmpeg and ensure it’s on PATH.
- No devices listed: Ensure `soundcard` is installed and you have at least one playback device enabled in Windows.
- GPU not used: Install the matching CUDA wheel via `-Torch cu121` or `-Torch cu122` in the bootstrap script, and verify your NVIDIA drivers.
- Whisper not installed: Install extras with `pip install .[whisper]`.

## Development

```
python -m pip install .[dev,whisper]
pre-commit install
pytest -q
```

- Lint/format: `ruff --fix . && black .` or `pre-commit run --all-files`
- Tests prefer the `DummyASR` backend to stay fast and deterministic.
