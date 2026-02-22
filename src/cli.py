"""Command-line interface for the transcription tool."""

import argparse
import json
import os
import sys
import time

from dotenv import load_dotenv
from pathlib import Path

from src.config import MAX_CHUNK_SECONDS, TEMP_DIR, TRANSCRIPTS_DIR
from src.downloader import download_from_youtube, download_from_url
from src.transcriber import transcribe
from src.utils import (
    DownloadError,
    TranscriptionError,
    AudioProcessingError,
    generate_filename,
    is_remote_url,
    is_youtube_url,
    logger,
    setup_logging,
)


def _save_transcript(text: str, source: str) -> str:
    """Save transcription text and metadata. Returns the text file path."""
    stem = generate_filename()

    text_path = TRANSCRIPTS_DIR / f"{stem}.txt"
    meta_path = TRANSCRIPTS_DIR / f"{stem}.json"

    text_path.write_text(text, encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {
                "source": source,
                "is_youtube": is_youtube_url(source),
                "word_count": len(text.split()),
                "timestamp": stem.split("_", 1)[1],  # everything after prefix
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    logger.info("Saved: %s", text_path)
    return str(text_path)


def _resolve_audio(source: str) -> tuple[str, bool]:
    """Download or locate the audio file.

    Returns (local_path, needs_cleanup).
    """
    if is_youtube_url(source):
        return download_from_youtube(source), True

    if is_remote_url(source):
        return download_from_url(source), True

    # Assume local file path.
    if not os.path.isfile(source):
        logger.error("File not found: %s", source)
        sys.exit(1)
    return source, False


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="transcribe",
        description="Transcribe YouTube videos, audio URLs, or local audio files.",
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="YouTube URL, audio file URL, or local file path. "
             "If omitted, you will be prompted interactively.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=None,
        help=f"Directory for transcript output (default: {TRANSCRIPTS_DIR})",
    )
    parser.add_argument(
        "--max-chunk",
        type=int,
        default=None,
        help=f"Max chunk duration in seconds (default: {MAX_CHUNK_SECONDS})",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    setup_logging(verbose=args.verbose)
    load_dotenv()

    if not os.environ.get("REPLICATE_API_TOKEN"):
        logger.error(
            "REPLICATE_API_TOKEN not set. "
            "Create a .env file or export the variable."
        )
        sys.exit(1)

    # Apply overrides from CLI flags.
    if args.output_dir is not None:
        import src.config as cfg
        cfg.TRANSCRIPTS_DIR = args.output_dir

    if args.max_chunk is not None:
        import src.config as cfg
        cfg.MAX_CHUNK_SECONDS = args.max_chunk

    # Ensure directories exist.
    TEMP_DIR.mkdir(exist_ok=True)
    TRANSCRIPTS_DIR.mkdir(exist_ok=True)

    # Get the source URL / path.
    source = args.url
    if not source:
        try:
            source = input("Enter URL (YouTube, audio URL, or local path): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

    if not source:
        logger.error("No input provided")
        sys.exit(1)

    audio_path: str | None = None
    needs_cleanup = False

    try:
        audio_path, needs_cleanup = _resolve_audio(source)

        start = time.time()
        text = transcribe(audio_path)
        elapsed = time.time() - start
        logger.info("Completed in %.1fs", elapsed)

        _save_transcript(text, source)

    except (DownloadError, TranscriptionError, AudioProcessingError) as e:
        logger.error("Error: %s", e)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nInterrupted")
        sys.exit(130)
    finally:
        if audio_path and needs_cleanup and os.path.exists(audio_path):
            os.remove(audio_path)
            logger.debug("Cleaned up temp file: %s", audio_path)


if __name__ == "__main__":
    main()
