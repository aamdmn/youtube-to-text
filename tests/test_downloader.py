"""Tests for src.downloader."""

from unittest.mock import MagicMock, patch, mock_open

import pytest

from src.downloader import download_from_youtube, download_from_url
from src.utils import DownloadError


class TestDownloadFromYoutube:
    @patch("src.downloader.yt_dlp.YoutubeDL")
    def test_success(self, mock_ydl_cls, tmp_path):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_ydl.extract_info.return_value = {"title": "Test Video"}
        mock_ydl.prepare_filename.return_value = "temp/Test Video.webm"

        result = download_from_youtube("https://www.youtube.com/watch?v=test")
        assert result == "temp/Test Video.mp3"

    @patch("src.downloader.yt_dlp.YoutubeDL")
    def test_failure_raises(self, mock_ydl_cls):
        mock_ydl_cls.side_effect = Exception("yt-dlp broke")

        with pytest.raises(DownloadError, match="YouTube download failed"):
            download_from_youtube("https://www.youtube.com/watch?v=bad")


class TestDownloadFromUrl:
    @patch("src.downloader.requests.get")
    def test_success(self, mock_get, tmp_path):
        # Mock the streaming response.
        mock_resp = MagicMock()
        mock_resp.headers = {"content-type": "audio/mpeg"}
        mock_resp.iter_content.return_value = [b"fake audio bytes"]
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_get.return_value = mock_resp

        # Patch TEMP_DIR to use tmp_path so files get created there.
        with patch("src.downloader.TEMP_DIR", tmp_path):
            result = download_from_url("https://example.com/podcast.mp3")

        assert result.endswith("podcast.mp3")

    @patch("src.downloader.requests.get")
    def test_failure_raises(self, mock_get):
        import requests
        mock_get.side_effect = requests.ConnectionError("nope")

        with pytest.raises(DownloadError, match="URL download failed"):
            download_from_url("https://example.com/bad.mp3")
