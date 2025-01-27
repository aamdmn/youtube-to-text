# Audio Transcription Tool

A simple tool to transcribe audio files and YouTube videos using Replicate's Whisper model.

## Setup

1. Install dependencies using `uv`:
```bash
uv pip install -e .
```

2. Create a `.env` file with your Replicate API token:
```bash
REPLICATE_API_TOKEN=your_token_here
```

3. Make sure you have FFmpeg installed:
   - macOS: `brew install ffmpeg`
   - Ubuntu/Debian: `sudo apt install ffmpeg`
   - Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html)

## Usage

1. Run the script:
```bash
uv run transcribe.py
```

2. Enter either:
   - A YouTube URL (e.g., https://www.youtube.com/watch?v=...)
   - A direct audio file URL

3. For YouTube videos, the script will:
   - Download the audio in MP3 format
   - Process the transcription using Whisper
   - Clean up temporary files

4. The script will create two files in the `transcripts` directory:
   - `transcript_[timestamp].txt`: Contains the plain text transcription
   - `metadata_[timestamp].json`: Contains metadata (source URL, timestamp)

## Features

- Supports YouTube videos and direct audio files
- Handles long audio files
- Downloads and processes YouTube videos locally
- English language transcription
- Progress tracking
- Error handling
- Saves transcription as plain text
- Stores metadata separately
- Environment variable configuration
- Automatic cleanup of temporary files

## Limitations

- Very large files may take longer to process
- Requires stable internet connection for API calls

## Troubleshooting

If you encounter issues:
- Ensure your Replicate API token is valid
- Check your internet connection
- For YouTube videos, ensure the URL is accessible
- Make sure you have sufficient disk space for temporary files
