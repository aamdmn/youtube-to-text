"""Utility functions: logging, validation, file naming."""

import logging
import random
import re
import string
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger("transcribe")


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter("%(message)s")

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger("transcribe")
    root.setLevel(level)
    root.addHandler(handler)


def is_youtube_url(url: str) -> bool:
    """Check if URL is from YouTube."""
    try:
        parsed = urlparse(url)
        return any(
            d in parsed.netloc
            for d in ["youtube.com", "youtu.be", "www.youtube.com"]
        )
    except Exception:
        return False


def is_remote_url(url: str) -> bool:
    """Check if a string is an HTTP/HTTPS URL."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https")
    except Exception:
        return False


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a filesystem-safe slug.

    Lowercases, replaces non-alphanumeric chars with hyphens, and trims.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text[:max_length].rstrip("-")


def generate_filename(
    prefix: str = "transcript",
    title: str | None = None,
    video_id: str | None = None,
) -> str:
    """Generate a unique filename.

    For YouTube videos with metadata:
        transcript_{video_id}_{title-slug}
    For other sources:
        transcript_{timestamp}_{random}

    Returns a stem (no extension).
    """
    if video_id:
        parts = [prefix, video_id]
        if title:
            parts.append(slugify(title))
        return "_".join(parts)

    # Fallback: timestamp + random suffix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{prefix}_{timestamp}_{suffix}"


class TranscriptionError(Exception):
    """Raised when the Replicate API transcription fails."""


class DownloadError(Exception):
    """Raised when audio download fails."""


class AudioProcessingError(Exception):
    """Raised when audio splitting or duration measurement fails."""
