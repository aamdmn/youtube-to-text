# youtube-to-text

Transcribe YouTube videos, audio URLs, and local audio files using OpenAI's `gpt-4o-transcribe` model via the Replicate API.

## Setup

1. Install dependencies using `uv`:
```bash
uv pip install -e ".[dev]"
```

2. Create a `.env` file with your Replicate API token:
```bash
cp .env.example .env
# then edit .env and add your token
```

3. Make sure you have FFmpeg installed:
   - macOS: `brew install ffmpeg`
   - Ubuntu/Debian: `sudo apt install ffmpeg`
   - Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html)

## Usage

### Command line

```bash
# Transcribe a YouTube video
transcribe "https://www.youtube.com/watch?v=..."

# Transcribe a direct audio URL
transcribe "https://example.com/podcast.mp3"

# Transcribe a local file
transcribe recording.m4a

# Interactive mode (prompts for input)
transcribe
```

### Options

```
positional arguments:
  url                   YouTube URL, audio file URL, or local file path.
                        If omitted, you will be prompted interactively.

options:
  -o, --output-dir DIR  Directory for transcript output (default: transcripts)
  --max-chunk SECONDS   Max chunk duration in seconds (default: 300)
  -v, --verbose         Enable debug logging
  -h, --help            Show help message
```

### Running without install

```bash
uv run -m src.cli "https://www.youtube.com/watch?v=..."
```

## How it works

1. **Download** — YouTube audio is extracted as MP3 via `yt-dlp` + FFmpeg. Direct audio URLs are streamed to disk. Local files are used as-is.
2. **Split** — Audio longer than 5 minutes is split into chunks at natural silence points (using `pydub` silence detection), avoiding mid-word cuts.
3. **Transcribe** — Each chunk is sent to the `gpt-4o-transcribe` model on Replicate. API calls are retried up to 3 times with exponential backoff.
4. **Validate** — Each chunk is checked for possible truncation (low word count relative to duration, missing terminal punctuation).
5. **Save** — The full transcript is saved as a `.txt` file alongside a `.json` metadata file in the output directory.
6. **Cleanup** — All temporary files are removed.

## Features

- YouTube videos, direct audio URLs, and local audio files
- Silence-based audio splitting for accurate chunk boundaries
- Truncation detection with warnings
- Retry logic with exponential backoff for API resilience
- CLI with argument parsing (also supports interactive mode)
- Structured logging with `--verbose` debug mode
- Automatic cleanup of temporary files

## Limitations

- Requires a valid Replicate API token and stable internet connection
- Very long files produce many API calls (billed per call)
- Transcription quality depends on audio clarity

## Troubleshooting

- **Truncated transcripts** — Try a smaller `--max-chunk` value (e.g., `--max-chunk 180`).
- **Download failures** — Ensure the URL is accessible and `yt-dlp` / FFmpeg are installed.
- **API errors** — Verify your `REPLICATE_API_TOKEN` is valid. The tool retries automatically on transient failures.
