import os
import json
import time
import base64
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse

import replicate
import yt_dlp
from dotenv import load_dotenv

def setup_environment() -> None:
    """Load environment variables and create necessary directories."""
    load_dotenv()
    Path("transcripts").mkdir(exist_ok=True)
    Path("temp").mkdir(exist_ok=True)

def get_data_uri(file_path: str) -> str:
    """
    Convert a file to a data URI.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Data URI string
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = 'audio/mpeg'  # Default to MP3
        
    with open(file_path, 'rb') as f:
        data = base64.b64encode(f.read()).decode()
    
    return f"data:{mime_type};base64,{data}"

def is_youtube_url(url: str) -> bool:
    """Check if the URL is a YouTube URL."""
    parsed = urlparse(url)
    return any(
        domain in parsed.netloc
        for domain in ['youtube.com', 'youtu.be', 'www.youtube.com']
    )

def download_youtube_audio(url: str) -> Optional[str]:
    """
    Download audio from YouTube video.
    
    Args:
        url: YouTube URL
        
    Returns:
        Path to downloaded audio file
    """
    print("Downloading audio from YouTube...")
    output_dir = Path("temp")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
            print(f"Audio downloaded successfully: {filename}")
            return filename
    except Exception as e:
        print(f"Error downloading YouTube audio: {str(e)}")
        return None

def get_audio_path(url: str) -> Optional[str]:
    """
    Process the input URL. If it's a YouTube URL, download and return local path.
    Otherwise, return the URL as is.
    """
    if is_youtube_url(url):
        return download_youtube_audio(url)
    return url

def transcribe_audio(audio_path: str, source_url: str) -> Dict[str, Any]:
    """
    Transcribe audio using Replicate's Whisper model.
    
    Args:
        audio_path: Path to audio file or URL
        source_url: Original source URL for cleanup reference
        
    Returns:
        Dict containing transcription results
    """
    print(f"Starting transcription...")
    start_time = time.time()
    
    try:
        if os.path.exists(audio_path):
            print("Using local audio file...")
            # Open the file and let Replicate handle the upload
            with open(audio_path, "rb") as audio_file:
                input_params = {
                    "audio": audio_file,  # Pass file object directly
                    "transcription": "plain text",
                    "translate": False,
                    "language": "en",
                    "temperature": 0,
                    "condition_on_previous_text": True,
                    "suppress_tokens": "-1",
                }
                output = replicate.run(
                    "openai/whisper:8099696689d249cf8b122d833c36ac3f75505c666a395ca40ef26f68e7d3d16e",
                    input=input_params,
                )
        else:
            # Handle URL case
            input_params = {
                "audio": audio_path,
                "transcription": "plain text",
                "translate": False,
                "language": "en",
                "temperature": 0,
                "condition_on_previous_text": True,
                "suppress_tokens": "-1",
            }
            output = replicate.run(
                "openai/whisper:8099696689d249cf8b122d833c36ac3f75505c666a395ca40ef26f26f68e7d3d16e",
                input=input_params
            )
        
        if not output:
            raise Exception("No output received from the API")
            
        elapsed_time = time.time() - start_time
        print(f"Transcription completed in {elapsed_time:.2f} seconds")
        
        # Ensure we have the required fields
        if not isinstance(output, dict):
            output = {"transcription": output, "detected_language": "unknown"}
        elif "transcription" not in output:
            # Some versions of the model return the text directly
            output = {"transcription": str(output), "detected_language": "unknown"}
            
        return {
            "transcription": output.get("transcription", ""),
            "detected_language": output.get("detected_language", "unknown")
        }
        
    except Exception as e:
        print(f"Error during transcription: {str(e)}")
        print(f"API Response: {output if 'output' in locals() else 'No response'}")
        raise
    finally:
        # Clean up downloaded files
        if os.path.exists(audio_path) and is_youtube_url(source_url):
            os.remove(audio_path)
            print("Cleaned up temporary audio file")

def save_transcript(transcript: Dict[str, str], source_url: str) -> str:
    """
    Save the transcript to a JSON file.
    
    Args:
        transcript: Dictionary containing transcription and detected language
        source_url: Original URL (YouTube or direct audio)
        
    Returns:
        Path to the saved transcript file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save plain text transcription
    text_filename = f"transcripts/transcript_{timestamp}.txt"
    with open(text_filename, 'w') as f:
        f.write(transcript["transcription"])
    
    # Save metadata in JSON
    json_filename = f"transcripts/metadata_{timestamp}.json"
    metadata = {
        "source_url": source_url,
        "is_youtube": is_youtube_url(source_url),
        "timestamp": timestamp,
        "detected_language": transcript["detected_language"],
        "text_file": text_filename
    }
    
    with open(json_filename, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Transcript saved to: {text_filename}")
    print(f"Metadata saved to: {json_filename}")
    return text_filename

def main():
    """Main function to handle audio transcription."""
    setup_environment()
    
    url = input("Enter the URL (YouTube or direct audio file): ").strip()
    
    if not url:
        print("Please provide a valid URL")
        return
    
    try:
        audio_path = get_audio_path(url)
        if not audio_path:
            print("Failed to process the URL")
            return
            
        transcript = transcribe_audio(audio_path, url)
        save_transcript(transcript, url)
        
    except Exception as e:
        print(f"Transcription failed: {str(e)}")
        return

if __name__ == "__main__":
    main() 