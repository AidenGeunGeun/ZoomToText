# ZoomToText

Command line tool for Windows that transcribes lecture audio and generates a
brief summary.  The pipeline runs ASR locally and sends the transcript to a
cloud LLM for summarization.

## Installation

Requires **Python 3.10+**.  Install the package and its runtime dependencies
with:

```
python -m pip install .[whisper]
```

This installs:

- `typer` – command line interface
- `openai` – OpenAI API client
- `sounddevice` – optional live audio capture
- `google-generativeai` – Gemini API client
- `openai-whisper` – optional local ASR backend

Upgrade `pip`/`setuptools` if installation fails:

```
python -m pip install --upgrade pip setuptools
```

## Usage

```
python -m zoom_to_text.cli transcribe --input input.wav --output outdir
```

To record audio directly from your system instead of using a file:

```
python -m zoom_to_text.cli transcribe --live --duration 30 --output outdir
```

The CLI accepts common audio formats (`.wav`, `.mp3`, `.m4a`) and video
containers such as `.mp4`; anything ffmpeg can decode will work. Low-confidence
segments in the transcript are marked with `[LOW CONFIDENCE]`.

Each run also writes a `segments.json` file containing per-segment metadata
(`start`, `end`, `confidence`, and `model`).

By default the CLI uses OpenAI Whisper for ASR and OpenAI ChatGPT for
summarization.  Provide an `OPENAI_API_KEY` (or `GEMINI_API_KEY`) environment
variable to enable summarization.  Without a key the tool falls back to
lightweight dummy implementations which are useful for testing.  Summarization
requests are chunked to handle long transcripts and include simple retry logic
for transient API errors.

To list available audio capture devices:

```
python -m zoom_to_text.cli transcribe --list-devices
```

## Development

```
python -m pip install .[whisper]
pytest
```
