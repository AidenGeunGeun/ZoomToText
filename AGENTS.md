# Repository Guidelines

## Project Structure & Module Organization
- Source code: `zoom_to_text/`
  - `cli.py` (Typer CLI), `asr.py` (Whisper/Dummy ASR), `pipeline.py` (I/O + orchestration), `capture.py` (audio devices/recording).
- Tests: `tests/` with `test_*.py` files.
- Outputs: Each run writes timestamped files to the chosen `--output-dir` (alias: `--output`): `transcript-YYYYMMDD-HHMMSS.txt` and `segments-YYYYMMDD-HHMMSS.json`.

## Build, Test, and Development Commands
- Install (with optional Whisper):
  - `python -m pip install .[whisper]`
- Run tests (pytest configured via `pyproject.toml`):
  - `pytest -q`
- Run CLI locally:
  - File input: `python -m zoom_to_text.cli transcribe --input input.wav --output-dir outdir`
  - System audio (loopback):
    - `python -m zoom_to_text.cli --list-devices` (note speaker index)
    - `python -m zoom_to_text.cli transcribe --live --device <index> --output-dir outdir`

## Coding Style & Naming Conventions
- Language: Python 3.10+ with type hints.
- Indentation: 4 spaces; line length ~100 chars; keep imports standard library → third‑party → local.
- Naming: modules/functions/variables `snake_case`; classes `PascalCase`.
- Docstrings: short, imperative summaries; prefer module and public API docstrings.
- Lint/format: Black + Ruff configured via pre-commit.
  - Install dev tools: `python -m pip install .[dev]`
  - Enable hooks: `pre-commit install` (runs on each commit)
  - One-time/full scan: `pre-commit run --all-files` or `ruff --fix . && black .`

## Testing Guidelines
- Framework: `pytest`.
- Location: `tests/`, files named `test_*.py`.
- Coverage: add tests for ASR logic and CLI paths (happy/error). Prefer fast, deterministic tests (use `DummyASR`).
- Run: `pytest -q` (CI-like quiet mode).

## Commit & Pull Request Guidelines
- Commits: concise, imperative subject (e.g., "improve device listing output"). Group related changes; avoid unrelated refactors.
- Prefer Conventional Commits types where practical: `feat:`, `fix:`, `chore:`, `test:`, `docs:`.
- PRs: include summary, motivation, testing instructions (exact CLI commands), and screenshots/logs if output changes. Link issues and note breaking changes.

## Security & Configuration Tips
- Windows-only scope. No API keys required (ASR runs locally).
- Loopback capture requires `soundcard`; it is installed by default. Do not commit generated artifacts (`output/`).

## Architecture Overview
- CLI resolves ASR backend, then calls `pipeline.process_audio()`.
- Pipeline writes transcript and per-segment metadata only (no summarization).
- Low‑confidence segments are flagged in the transcript.
