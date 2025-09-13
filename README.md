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
 - FFmpeg on PATH (required). Verify with: `ffmpeg -version`

## Install

Option A — bootstrap script (recommended):

1) Open PowerShell in the repo folder
2) Run:

```
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -Torch cpu -InstallFFmpeg
```

- Creates `.venv`, upgrades pip, installs `soundcard` (loopback), PyTorch (CPU), Whisper, and FFmpeg (via winget/choco when available).
- For NVIDIA GPU, use `-Torch cu121` or `-Torch cu122` instead of `cpu`.

Option B — manual steps (use a virtual environment):

```
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
winget install -e --id Gyan.FFmpeg  # or install FFmpeg by your preferred method
ffmpeg -version  # verify it's on PATH
python -m pip install --upgrade pip setuptools wheel
python -m pip install soundcard
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
python -m pip install .
```

Notes:
- Always install inside your virtual environment.
- FFmpeg is required; Whisper uses it for robust decoding/resampling.
- Loopback capture uses `soundcard` and records at 48 kHz to match Windows shared mode.

## Usage

First, activate the venv (Powershell):

```
.venv\Scripts\Activate.ps1
```


List devices (loopback speakers):

```
python -m zoom_to_text.cli --list-devices
```

Transcribe a file:

```
python -m zoom_to_text.cli --input input.wav --output-dir outdir
```

Capture system audio (live) until Ctrl+C:

```
python -m zoom_to_text.cli --live --device <index> --output-dir outdir
```

Note: Live capture records at 48 kHz; Whisper+FFmpeg will handle resampling/downmixing.

Model selection:
- Default is `--asr-model turbo`; if unavailable, falls back to `large-v3` automatically.
- You can choose other Whisper models (e.g., `small`, `base`, `large-v3`) or `dummy` for tests.

Outputs (no overwrites):
- `transcript-YYYYMMDD-HHMMSS.txt`
- `segments-YYYYMMDD-HHMMSS.json`

Tip: `--output-dir` also has an alias `--output`.

## Troubleshooting
- FFmpeg missing: If you see an error like "ffmpeg is required but was not found in PATH", install FFmpeg (e.g., `winget install -e --id Gyan.FFmpeg`) and ensure `ffmpeg` runs in your terminal.
- No devices listed: Ensure `soundcard` is installed and you have at least one playback device enabled in Windows.
- GPU not used: Install the matching CUDA wheel via `-Torch cu121` or `-Torch cu122` in the bootstrap script, and verify your NVIDIA drivers.
- Whisper not installed: Reinstall the project (`pip install .`) after ensuring PyTorch is installed; see above. Whisper is a required dependency.

## Development

```
python -m pip install .[dev]
pre-commit install
pytest -q
```

- Lint/format: `ruff --fix . && black .` or `pre-commit run --all-files`
- Tests prefer the `DummyASR` backend to stay fast and deterministic.
