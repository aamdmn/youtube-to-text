"""Transcription via Replicate API with retry logic and truncation detection."""

import time

import replicate

from src.audio import cleanup_files, get_duration_seconds, split_audio
from src.config import (
    DEFAULT_MODEL,
    EXPECTED_WORDS_PER_SECOND,
    MAX_CHUNK_SECONDS,
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    TRANSCRIPTION_TEMPERATURE,
    TRUNCATION_WARN_RATIO,
)
from src.utils import TranscriptionError, logger


def _transcribe_file(path: str) -> str:
    """Transcribe a single audio file via the Replicate API.

    Retries up to MAX_RETRIES times with exponential backoff on transient
    failures.  Raises TranscriptionError on permanent failure.
    """
    last_err: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with open(path, "rb") as f:
                output = replicate.run(
                    DEFAULT_MODEL,
                    input={"audio_file": f, "temperature": TRANSCRIPTION_TEMPERATURE},
                )

            if output is None:
                raise TranscriptionError("API returned no response")

            tokens = list(output)
            text = "".join(tokens)

            if not text.strip():
                raise TranscriptionError("API returned empty transcription")

            return text

        except TranscriptionError:
            raise  # don't retry on clearly bad responses
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "  Attempt %d/%d failed (%s), retrying in %ds...",
                    attempt, MAX_RETRIES, e, delay,
                )
                time.sleep(delay)
            else:
                logger.error("  All %d attempts failed", MAX_RETRIES)

    raise TranscriptionError(
        f"Transcription failed after {MAX_RETRIES} attempts: {last_err}"
    )


def _check_truncation(text: str, chunk_duration_s: float, chunk_index: int) -> None:
    """Warn if a chunk transcription appears truncated."""
    word_count = len(text.split())
    expected_words = chunk_duration_s * EXPECTED_WORDS_PER_SECOND
    ratio = word_count / expected_words if expected_words > 0 else 1.0

    if ratio < TRUNCATION_WARN_RATIO:
        logger.warning(
            "  Chunk %d may be truncated: got %d words, expected ~%d "
            "(%.0f%% of estimate)",
            chunk_index + 1, word_count, int(expected_words), ratio * 100,
        )

    # Also flag if the text ends without terminal punctuation.
    stripped = text.rstrip()
    if stripped and stripped[-1] not in ".?!\"'":
        logger.warning(
            "  Chunk %d ends without terminal punctuation — possible truncation",
            chunk_index + 1,
        )


def transcribe(audio_path: str) -> str:
    """Transcribe an audio file, splitting into chunks if needed.

    Returns the full transcription text.
    """
    duration = get_duration_seconds(audio_path)
    logger.info("Duration: %.0fs (%.1f min)", duration, duration / 60)

    # Short file — transcribe directly.
    if duration <= MAX_CHUNK_SECONDS:
        logger.info("Transcribing...")
        text = _transcribe_file(audio_path)
        _check_truncation(text, duration, 0)
        return text

    # Long file — split and transcribe each chunk.
    chunks = split_audio(audio_path)
    transcriptions: list[str] = []

    try:
        for i, chunk_path in enumerate(chunks):
            logger.info("Transcribing chunk %d/%d...", i + 1, len(chunks))
            chunk_dur = get_duration_seconds(chunk_path)
            text = _transcribe_file(chunk_path)
            _check_truncation(text, chunk_dur, i)
            transcriptions.append(text)
    finally:
        cleanup_files(chunks)

    return "\n\n".join(transcriptions)
