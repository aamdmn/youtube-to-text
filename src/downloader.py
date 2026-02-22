"""Audio download: YouTube via yt-dlp, direct URLs via requests."""

import requests
import yt_dlp
from pathlib import Path

from src.config import AUDIO_QUALITY, TEMP_DIR
from src.utils import DownloadError, logger


def download_from_youtube(url: str) -> str:
    """Download audio from a YouTube URL. Returns path to the mp3 file."""
    logger.info("Downloading audio from YouTube...")

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": AUDIO_QUALITY,
            }
        ],
        "outtmpl": str(TEMP_DIR / "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".mp3"
            logger.info("Downloaded: %s", path)
            return path
    except Exception as e:
        raise DownloadError(f"YouTube download failed: {e}") from e


def download_from_url(url: str) -> str:
    """Download an audio file from a direct HTTP(S) URL.

    Streams the file to TEMP_DIR and returns the local path.
    """
    logger.info("Downloading audio from URL...")

    # Derive a filename from the URL path, fall back to a generic name.
    url_path = Path(url.split("?")[0].split("#")[0])
    filename = url_path.name or "audio_download"
    # Ensure it has an extension; default to .mp3
    if "." not in filename:
        filename += ".mp3"

    dest = TEMP_DIR / filename

    try:
        with requests.get(url, stream=True, timeout=120) as resp:
            resp.raise_for_status()

            # Quick sanity check on content-type
            ct = resp.headers.get("content-type", "")
            if ct and "audio" not in ct and "octet-stream" not in ct:
                logger.warning(
                    "URL content-type is '%s' — may not be an audio file", ct
                )

            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

        logger.info("Downloaded: %s", dest)
        return str(dest)

    except requests.RequestException as e:
        raise DownloadError(f"URL download failed: {e}") from e
