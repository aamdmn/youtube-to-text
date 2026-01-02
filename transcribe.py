"""YouTube/Audio to Text Transcription Tool"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import replicate
import yt_dlp
from dotenv import load_dotenv
from pydub import AudioSegment

# API has 2000 token output limit (~1500 words)
# At ~150 words/min speaking rate, ~10 min chunks are safe
MAX_CHUNK_SECONDS = 600


def setup():
    """Initialize environment and directories."""
    load_dotenv()
    Path("transcripts").mkdir(exist_ok=True)
    Path("temp").mkdir(exist_ok=True)


def is_youtube_url(url: str) -> bool:
    """Check if URL is from YouTube."""
    parsed = urlparse(url)
    return any(d in parsed.netloc for d in ["youtube.com", "youtu.be", "www.youtube.com"])


def download_from_youtube(url: str) -> str | None:
    """Download audio from YouTube, return path to mp3 file."""
    print("Downloading audio from YouTube...")

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "outtmpl": "temp/%(title)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".mp3"
            print(f"Downloaded: {path}")
            return path
    except Exception as e:
        print(f"Download failed: {e}")
        return None


def get_audio_duration_seconds(path: str) -> float:
    """Get duration of audio file in seconds."""
    audio = AudioSegment.from_file(path)
    return len(audio) / 1000.0


def split_audio_file(path: str) -> list[str]:
    """Split audio file into chunks under MAX_CHUNK_SECONDS."""
    print(f"Splitting audio into {MAX_CHUNK_SECONDS}s chunks...")

    audio = AudioSegment.from_file(path)
    chunk_ms = MAX_CHUNK_SECONDS * 1000
    base_name = Path(path).stem
    chunks = []

    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        end = min(start + chunk_ms, len(audio))
        chunk = audio[start:end]

        chunk_path = f"temp/{base_name}_chunk_{i:03d}.mp3"
        chunk.export(chunk_path, format="mp3")
        chunks.append(chunk_path)

        print(f"  Chunk {i + 1}: {start/1000:.0f}s - {end/1000:.0f}s")

    print(f"Created {len(chunks)} chunks")
    return chunks


def transcribe_file(path: str) -> str:
    """
    Transcribe a single audio file using gpt-4o-transcribe.
    Returns the transcribed text.
    """
    with open(path, "rb") as f:
        output = replicate.run(
            "openai/gpt-4o-transcribe",
            input={"audio_file": f, "temperature": 0},
        )

    # API returns iterator of string tokens - join them
    if output is None:
        raise Exception("No response from API")

    # Handle both iterator and list responses
    tokens = list(output)
    return "".join(tokens)


def transcribe(audio_path: str) -> str:
    """
    Transcribe audio file, automatically splitting if too long.
    Returns full transcription text.
    """
    duration = get_audio_duration_seconds(audio_path)
    print(f"Duration: {duration:.0f}s ({duration/60:.1f} min)")

    chunks_to_cleanup = []

    try:
        if duration <= MAX_CHUNK_SECONDS:
            # Short file - transcribe directly
            print("Transcribing...")
            return transcribe_file(audio_path)

        # Long file - split and transcribe chunks
        chunks_to_cleanup = split_audio_file(audio_path)
        transcriptions = []

        for i, chunk_path in enumerate(chunks_to_cleanup):
            print(f"Transcribing chunk {i + 1}/{len(chunks_to_cleanup)}...")
            text = transcribe_file(chunk_path)
            transcriptions.append(text)

        return "\n\n".join(transcriptions)

    finally:
        # Cleanup chunk files
        for chunk in chunks_to_cleanup:
            if os.path.exists(chunk):
                os.remove(chunk)


def save_transcript(text: str, source_url: str) -> str:
    """Save transcript to file, return path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save text
    text_path = f"transcripts/transcript_{timestamp}.txt"
    with open(text_path, "w") as f:
        f.write(text)

    # Save metadata
    meta_path = f"transcripts/metadata_{timestamp}.json"
    with open(meta_path, "w") as f:
        json.dump({
            "source_url": source_url,
            "is_youtube": is_youtube_url(source_url),
            "timestamp": timestamp,
        }, f, indent=2)

    print(f"Saved: {text_path}")
    return text_path


def main():
    setup()

    url = input("Enter URL (YouTube or audio file): ").strip()
    if not url:
        print("No URL provided")
        return

    audio_path = None
    try:
        # Get audio file
        if is_youtube_url(url):
            audio_path = download_from_youtube(url)
            if not audio_path:
                return
        else:
            audio_path = url

        # Transcribe
        start = time.time()
        text = transcribe(audio_path)
        print(f"Completed in {time.time() - start:.1f}s")

        # Save
        save_transcript(text, url)

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Cleanup downloaded file
        if audio_path and is_youtube_url(url) and os.path.exists(audio_path):
            os.remove(audio_path)
            print("Cleaned up temp file")


if __name__ == "__main__":
    main()
