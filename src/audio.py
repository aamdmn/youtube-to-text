"""Audio processing: duration measurement and silence-based splitting."""

import os
from pathlib import Path

from pydub import AudioSegment
from pydub.silence import detect_silence

from src.config import (
    MAX_CHUNK_SECONDS,
    MIN_SILENCE_MS,
    SILENCE_THRESH_DB,
    SPLIT_WINDOW_SECONDS,
    TEMP_DIR,
)
from src.utils import AudioProcessingError, logger


def get_duration_seconds(path: str) -> float:
    """Get duration of an audio file in seconds."""
    try:
        audio = AudioSegment.from_file(path)
        return len(audio) / 1000.0
    except Exception as e:
        raise AudioProcessingError(f"Failed to read audio file: {e}") from e


def _find_silence_near(audio: AudioSegment, target_ms: int) -> int | None:
    """Find the best silence point near `target_ms`.

    Searches within a window of ±SPLIT_WINDOW_SECONDS around the target.
    Returns the midpoint (in ms) of the silence segment closest to the target,
    or None if no silence is found in the window.
    """
    window_ms = SPLIT_WINDOW_SECONDS * 1000
    search_start = max(0, target_ms - window_ms)
    search_end = min(len(audio), target_ms + window_ms)
    segment = audio[search_start:search_end]

    silences = detect_silence(
        segment,
        min_silence_len=MIN_SILENCE_MS,
        silence_thresh=SILENCE_THRESH_DB,
    )

    if not silences:
        return None

    # Each silence is [start_ms, end_ms] relative to the segment.
    # Convert to absolute positions and pick the one closest to target.
    best = None
    best_dist = float("inf")
    for start, end in silences:
        midpoint = search_start + (start + end) // 2
        dist = abs(midpoint - target_ms)
        if dist < best_dist:
            best_dist = dist
            best = midpoint

    return best


def split_audio(path: str) -> list[str]:
    """Split an audio file into chunks, cutting at silence points.

    Tries to split near every MAX_CHUNK_SECONDS boundary at a natural
    pause. Falls back to a hard cut if no silence is found nearby.

    Returns a list of file paths for the chunk files (stored in TEMP_DIR).
    """
    try:
        audio = AudioSegment.from_file(path)
    except Exception as e:
        raise AudioProcessingError(f"Failed to load audio for splitting: {e}") from e

    total_ms = len(audio)
    chunk_target_ms = MAX_CHUNK_SECONDS * 1000
    base_name = Path(path).stem
    chunks: list[str] = []

    logger.info("Splitting audio into ~%ds chunks...", MAX_CHUNK_SECONDS)

    pos = 0
    i = 0
    while pos < total_ms:
        # If the remaining audio fits in one chunk, take it all.
        if total_ms - pos <= chunk_target_ms:
            end = total_ms
        else:
            target = pos + chunk_target_ms
            silence_point = _find_silence_near(audio, target)
            if silence_point is not None:
                end = silence_point
                logger.debug(
                    "  Chunk %d: splitting at silence %0.1fs (target was %0.1fs)",
                    i + 1, end / 1000, target / 1000,
                )
            else:
                end = target
                logger.debug(
                    "  Chunk %d: no silence found, hard split at %0.1fs",
                    i + 1, end / 1000,
                )

        chunk = audio[pos:end]
        chunk_path = str(TEMP_DIR / f"{base_name}_chunk_{i:03d}.mp3")
        chunk.export(chunk_path, format="mp3")
        chunks.append(chunk_path)

        duration_s = (end - pos) / 1000
        logger.info(
            "  Chunk %d: %.1fs - %.1fs (%.1fs)",
            i + 1, pos / 1000, end / 1000, duration_s,
        )

        pos = end
        i += 1

    logger.info("Created %d chunks", len(chunks))
    return chunks


def cleanup_files(paths: list[str]) -> None:
    """Remove a list of files, ignoring errors."""
    for p in paths:
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            logger.debug("Failed to remove temp file: %s", p)
