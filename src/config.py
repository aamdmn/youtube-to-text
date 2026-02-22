"""Constants and configuration for the transcription tool."""

from pathlib import Path

# Directories
TEMP_DIR = Path("temp")
TRANSCRIPTS_DIR = Path("transcripts")

# Audio splitting
# 5-minute chunks keep output well within the API's ~2000 token limit,
# even for fast speakers (~200 wpm = ~1000 words in 5 min).
MAX_CHUNK_SECONDS = 300

# Window (in seconds) around the target split point to search for silence.
SPLIT_WINDOW_SECONDS = 30

# pydub silence detection parameters
SILENCE_THRESH_DB = -40  # dBFS threshold to consider as silence
MIN_SILENCE_MS = 400     # minimum silence length to be a valid split point

# Audio download quality (kbps)
AUDIO_QUALITY = "192"

# Replicate model
DEFAULT_MODEL = "openai/gpt-4o-transcribe"
TRANSCRIPTION_TEMPERATURE = 0

# Retry settings for API calls
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds; doubles each attempt (2s, 4s, 8s)

# Truncation detection
# If actual words < expected words * this ratio, warn about possible truncation.
TRUNCATION_WARN_RATIO = 0.5
# Assumed average speaking rate for truncation estimates (words per second).
EXPECTED_WORDS_PER_SECOND = 2.5
