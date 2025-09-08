# ZoomToText

Command line tool that transcribes lecture audio and generates a brief summary.

## Usage

```
python -m zoom_to_text.cli transcribe --input input.wav --output outdir
```

To record audio directly from your system instead of using a file:

```
python -m zoom_to_text.cli transcribe --live --duration 30 --output outdir
```

The CLI accepts common audio formats (`.wav`, `.mp3`, `.m4a`) and video
containers such as `.mp4`; anything ffmpeg can decode will work.

By default the CLI uses OpenAI Whisper for ASR and OpenAI ChatGPT for
summarization.  Provide an `OPENAI_API_KEY` environment variable to enable
summarization.  Without a key the tool falls back to lightweight dummy
implementations which are useful for testing.

## Development

```
python -m pip install .[whisper]
pytest
```
