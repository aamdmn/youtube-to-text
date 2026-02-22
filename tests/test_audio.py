"""Tests for src.audio."""

import os
import math

import pytest
from pydub import AudioSegment
from pydub.generators import Sine, WhiteNoise

from src.audio import get_duration_seconds, split_audio, cleanup_files, _find_silence_near
from src.config import TEMP_DIR


@pytest.fixture(autouse=True)
def ensure_temp_dir():
    """Make sure the temp directory exists for chunk output."""
    TEMP_DIR.mkdir(exist_ok=True)
    yield


@pytest.fixture
def short_audio(tmp_path):
    """Create a 10-second sine wave audio file."""
    tone = Sine(440).to_audio_segment(duration=10_000)  # 10s
    path = str(tmp_path / "short.mp3")
    tone.export(path, format="mp3")
    return path


@pytest.fixture
def long_audio_with_silence(tmp_path):
    """Create a ~12-minute audio file with silence gaps every ~4 minutes.

    Pattern: 4 min tone | 1s silence | 4 min tone | 1s silence | 4 min tone
    Total: ~12 minutes.
    """
    tone_4min = Sine(440).to_audio_segment(duration=240_000)
    silence_1s = AudioSegment.silent(duration=1000)

    audio = tone_4min + silence_1s + tone_4min + silence_1s + tone_4min
    path = str(tmp_path / "long_with_silence.mp3")
    audio.export(path, format="mp3")
    return path


class TestGetDurationSeconds:
    def test_known_duration(self, short_audio):
        dur = get_duration_seconds(short_audio)
        assert abs(dur - 10.0) < 0.5  # allow small codec variance

    def test_nonexistent_file(self):
        with pytest.raises(Exception):
            get_duration_seconds("/nonexistent/file.mp3")


class TestFindSilenceNear:
    def test_finds_silence(self):
        """Should find the silence gap in a tone-silence-tone pattern."""
        tone = Sine(440).to_audio_segment(duration=5000)
        silence = AudioSegment.silent(duration=1000)
        audio = tone + silence + tone  # 5s tone, 1s silence, 5s tone

        # Target is at 6000ms (middle of the audio); silence is at 5000-6000ms.
        result = _find_silence_near(audio, target_ms=6000)
        assert result is not None
        # The midpoint of the silence should be near 5500ms.
        assert abs(result - 5500) < 500

    def test_no_silence(self):
        """Should return None when there is no silence in the window."""
        tone = Sine(440).to_audio_segment(duration=10_000)
        result = _find_silence_near(tone, target_ms=5000)
        assert result is None


class TestSplitAudio:
    def test_splits_long_file(self, long_audio_with_silence):
        chunks = split_audio(long_audio_with_silence)
        try:
            assert len(chunks) >= 2
            # All chunk files should exist.
            for c in chunks:
                assert os.path.isfile(c)
            # Total duration of chunks should roughly equal the original.
            total = sum(get_duration_seconds(c) for c in chunks)
            original = get_duration_seconds(long_audio_with_silence)
            assert abs(total - original) < 2.0  # within 2s
        finally:
            cleanup_files(chunks)


class TestCleanupFiles:
    def test_removes_existing(self, tmp_path):
        p = str(tmp_path / "deleteme.txt")
        with open(p, "w") as f:
            f.write("x")
        cleanup_files([p])
        assert not os.path.exists(p)

    def test_ignores_missing(self):
        # Should not raise.
        cleanup_files(["/nonexistent/file.txt"])
