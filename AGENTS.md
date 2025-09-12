# Repository Guidelines

## Project Structure & Module Organization
- Source: `zoom_to_text/`
  - `cli.py` (Typer CLI), `asr.py` (Whisper/Dummy ASR), `pipeline.py` (I/O + orchestration), `capture.py` (audio devices/recording).
- Tests: `tests/` with `test_*.py` files.
- Outputs: Each run writes timestamped files to the chosen `--output-dir` (alias `--output`): `transcript-YYYYMMDD-HHMMSS.txt` and `segments-YYYYMMDD-HHMMSS.json`.

## Build, Test, and Development Commands
- Install: `python -m pip install .`
- ffmpeg is required (system binary). Verify: `ffmpeg -version`
- Dev tools (Black/Ruff/pre-commit): `python -m pip install .[dev]`
- Run tests (quiet): `pytest -q`
- CLI examples:
  - File input: `python -m zoom_to_text.cli --input input.wav --output-dir outdir`
  - List devices: `python -m zoom_to_text.cli --list-devices`
  - Live capture: `python -m zoom_to_text.cli --live --device <index> --output-dir outdir`

## Coding Style & Naming Conventions
- Python 3.10+ with type hints. Indent 4 spaces; target ~100 char lines.
- Imports ordered: standard library → third‑party → local.
- Names: `snake_case` for modules/functions/vars; `PascalCase` for classes.
- Docstrings: short, imperative summaries; prefer module and public API docs.
- Lint/format: Ruff + Black via pre-commit.
  - Enable hooks: `pre-commit install`
  - One-time/full scan: `pre-commit run --all-files` or `ruff --fix . && black .`

## Testing Guidelines
- Framework: `pytest`. Keep tests fast/deterministic; prefer `DummyASR` for ASR tests.
- Location/naming: `tests/` with `test_*.py`.
- Coverage focus: ASR logic and CLI happy/error paths.
- Run: `pytest -q`.

## Commit & Pull Request Guidelines
- Commits: concise, imperative subjects; group related changes. Prefer Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`).
- PRs: include summary, motivation, exact CLI commands to reproduce, and logs/screenshots if output changes. Link issues and note breaking changes.

## Security & Configuration Tips
- Windows-only scope. No API keys; ASR runs locally.
- Loopback capture requires `soundcard` (installed by default). ffmpeg must be present in PATH.
- Do not commit generated artifacts (e.g., `outdir/`). Respect user privacy; process audio locally.

## Architecture Overview
- CLI resolves ASR backend (Whisper or Dummy), then calls `pipeline.process_audio()`.
- Whisper is a required dependency; ffmpeg handles decoding/resampling. Live capture records at 48 kHz (stereo) to match Windows shared mode.
- Pipeline writes transcript and per-segment metadata only; low‑confidence segments are flagged in the transcript.
- `capture.py` lists/selects devices and handles loopback recording (filters benign discontinuity warnings).
