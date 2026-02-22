"""Tests for src.utils."""

import re

from src.utils import generate_filename, is_remote_url, is_youtube_url


class TestIsYoutubeUrl:
    def test_standard_url(self):
        assert is_youtube_url("https://www.youtube.com/watch?v=abc123")

    def test_short_url(self):
        assert is_youtube_url("https://youtu.be/abc123")

    def test_no_www(self):
        assert is_youtube_url("https://youtube.com/watch?v=abc123")

    def test_non_youtube(self):
        assert not is_youtube_url("https://vimeo.com/123456")

    def test_empty_string(self):
        assert not is_youtube_url("")

    def test_garbage(self):
        assert not is_youtube_url("not a url at all")

    def test_local_path(self):
        assert not is_youtube_url("/tmp/audio.mp3")


class TestIsRemoteUrl:
    def test_https(self):
        assert is_remote_url("https://example.com/audio.mp3")

    def test_http(self):
        assert is_remote_url("http://example.com/audio.mp3")

    def test_local_path(self):
        assert not is_remote_url("/tmp/audio.mp3")

    def test_relative_path(self):
        assert not is_remote_url("audio.mp3")

    def test_empty(self):
        assert not is_remote_url("")


class TestGenerateFilename:
    def test_has_timestamp_and_suffix(self):
        name = generate_filename()
        # Format: transcript_YYYYMMDD_HHMMSS_xxxx
        assert re.match(r"transcript_\d{8}_\d{6}_[a-z0-9]{4}$", name)

    def test_custom_prefix(self):
        name = generate_filename(prefix="custom")
        assert name.startswith("custom_")

    def test_unique(self):
        names = {generate_filename() for _ in range(20)}
        # With 4-char random suffix, collisions in 20 calls are extremely unlikely.
        assert len(names) == 20
