"""Tests for src.transcriber."""

from unittest.mock import MagicMock, patch

import pytest

from src.transcriber import _transcribe_file, _check_truncation
from src.utils import TranscriptionError


class TestTranscribeFile:
    @patch("src.transcriber.replicate")
    def test_success(self, mock_replicate, tmp_path):
        """Successful API call returns joined tokens."""
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"fake audio data")

        mock_replicate.run.return_value = iter(["Hello ", "world."])

        result = _transcribe_file(str(audio))
        assert result == "Hello world."

    @patch("src.transcriber.replicate")
    def test_empty_response_raises(self, mock_replicate, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"fake audio data")

        mock_replicate.run.return_value = iter([""])

        with pytest.raises(TranscriptionError, match="empty"):
            _transcribe_file(str(audio))

    @patch("src.transcriber.replicate")
    def test_none_response_raises(self, mock_replicate, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"fake audio data")

        mock_replicate.run.return_value = None

        with pytest.raises(TranscriptionError, match="no response"):
            _transcribe_file(str(audio))

    @patch("src.transcriber.time.sleep")  # don't actually sleep in tests
    @patch("src.transcriber.replicate")
    def test_retries_on_transient_error(self, mock_replicate, mock_sleep, tmp_path):
        """Should retry and succeed on the second attempt."""
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"fake audio data")

        mock_replicate.run.side_effect = [
            ConnectionError("network blip"),
            iter(["Recovered ", "text."]),
        ]

        result = _transcribe_file(str(audio))
        assert result == "Recovered text."
        assert mock_replicate.run.call_count == 2

    @patch("src.transcriber.time.sleep")
    @patch("src.transcriber.replicate")
    def test_exhausts_retries(self, mock_replicate, mock_sleep, tmp_path):
        """Should raise after all retry attempts are exhausted."""
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"fake audio data")

        mock_replicate.run.side_effect = ConnectionError("persistent failure")

        with pytest.raises(TranscriptionError, match="3 attempts"):
            _transcribe_file(str(audio))


class TestCheckTruncation:
    def test_no_warning_for_normal_text(self, caplog):
        """300s chunk with ~750 words (2.5 w/s) should not warn."""
        text = " ".join(["word"] * 750) + "."
        with caplog.at_level("WARNING"):
            _check_truncation(text, chunk_duration_s=300, chunk_index=0)
        assert "truncated" not in caplog.text.lower()

    def test_warns_on_low_word_count(self, caplog):
        """300s chunk with only 100 words should warn."""
        text = " ".join(["word"] * 100) + "."
        with caplog.at_level("WARNING"):
            _check_truncation(text, chunk_duration_s=300, chunk_index=0)
        assert "truncated" in caplog.text.lower() or "may be" in caplog.text.lower()

    def test_warns_on_missing_punctuation(self, caplog):
        """Text ending without punctuation should warn."""
        text = "This sentence has no ending"
        with caplog.at_level("WARNING"):
            _check_truncation(text, chunk_duration_s=60, chunk_index=0)
        assert "punctuation" in caplog.text.lower()
