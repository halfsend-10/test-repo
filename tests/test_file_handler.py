"""Tests for the file handler module.

Verifies correct saving and loading of files with various sizes and
character encodings, particularly multibyte UTF-8 content that crosses
the 64KB buffer boundary.
"""

import os
import tempfile

import pytest

from src.file_handler import BUFFER_SIZE, load_file, save_file


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestSaveFile:
    """Tests for save_file function."""

    def test_save_small_ascii_file(self, tmp_dir):
        """Save a small ASCII file successfully."""
        filepath = os.path.join(tmp_dir, "small.txt")
        content = "Hello, world!"
        bytes_written = save_file(content, filepath)
        assert bytes_written == len(content.encode("utf-8"))
        assert os.path.exists(filepath)

    def test_save_small_utf8_file(self, tmp_dir):
        """Save a small file with multibyte UTF-8 characters."""
        filepath = os.path.join(tmp_dir, "small_utf8.txt")
        content = "Hello 🌍🌎🌏 World"
        bytes_written = save_file(content, filepath)
        assert bytes_written == len(content.encode("utf-8"))
        assert os.path.exists(filepath)

    def test_save_60kb_utf8_file(self, tmp_dir):
        """Save ~60KB file with emoji/CJK characters (under buffer boundary)."""
        filepath = os.path.join(tmp_dir, "60kb_utf8.txt")
        # Each emoji is 4 bytes in UTF-8; build ~60KB of emoji content
        emoji_char = "🎉"
        char_count = (60 * 1024) // len(emoji_char.encode("utf-8"))
        content = emoji_char * char_count
        bytes_written = save_file(content, filepath)
        assert bytes_written == len(content.encode("utf-8"))
        assert bytes_written < BUFFER_SIZE

    def test_save_70kb_utf8_file(self, tmp_dir):
        """Save ~70KB file with emoji/CJK characters (over buffer boundary).

        This is the primary regression test for the segfault reported in
        issue #1737. Previously, the buffer was allocated using character
        count instead of byte length, causing a buffer overflow when
        multibyte characters pushed the actual byte count past 64KB.
        """
        filepath = os.path.join(tmp_dir, "70kb_utf8.txt")
        # Each emoji is 4 bytes in UTF-8; build ~70KB of emoji content
        emoji_char = "🎉"
        char_count = (70 * 1024) // len(emoji_char.encode("utf-8"))
        content = emoji_char * char_count
        byte_len = len(content.encode("utf-8"))
        assert byte_len > BUFFER_SIZE, "Test content must exceed buffer size"
        bytes_written = save_file(content, filepath)
        assert bytes_written == byte_len

    def test_save_256kb_mixed_content(self, tmp_dir):
        """Save ~256KB file with mixed ASCII and multibyte characters."""
        filepath = os.path.join(tmp_dir, "256kb_mixed.txt")
        # Mix of ASCII and multibyte characters
        segment = "Hello 世界! 🌍 Café résumé naïve "
        repeat_count = (256 * 1024) // len(segment.encode("utf-8"))
        content = segment * repeat_count
        byte_len = len(content.encode("utf-8"))
        assert byte_len > BUFFER_SIZE
        bytes_written = save_file(content, filepath)
        assert bytes_written == byte_len

    def test_save_empty_file(self, tmp_dir):
        """Save an empty file successfully."""
        filepath = os.path.join(tmp_dir, "empty.txt")
        bytes_written = save_file("", filepath)
        assert bytes_written == 0
        assert os.path.exists(filepath)

    def test_save_none_raises(self, tmp_dir):
        """Saving None content raises ValueError."""
        filepath = os.path.join(tmp_dir, "none.txt")
        with pytest.raises(ValueError, match="content must not be None"):
            save_file(None, filepath)

    def test_save_creates_parent_directories(self, tmp_dir):
        """Save creates intermediate directories if needed."""
        filepath = os.path.join(tmp_dir, "sub", "dir", "file.txt")
        save_file("test content", filepath)
        assert os.path.exists(filepath)


class TestRoundTrip:
    """Tests for save + load round-trip integrity."""

    def test_roundtrip_ascii(self, tmp_dir):
        """ASCII content survives a save/load round-trip."""
        filepath = os.path.join(tmp_dir, "ascii_rt.txt")
        content = "Simple ASCII content\nwith newlines\n"
        save_file(content, filepath)
        loaded = load_file(filepath)
        assert loaded == content

    def test_roundtrip_utf8_emoji(self, tmp_dir):
        """Emoji content survives a save/load round-trip."""
        filepath = os.path.join(tmp_dir, "emoji_rt.txt")
        content = "Emoji: 😀🎉🚀💡🔥 and text"
        save_file(content, filepath)
        loaded = load_file(filepath)
        assert loaded == content

    def test_roundtrip_70kb_emoji(self, tmp_dir):
        """70KB emoji content survives a save/load round-trip byte-for-byte.

        Verifies that saved content matches original after reload, ensuring
        no truncation or corruption at buffer boundaries.
        """
        filepath = os.path.join(tmp_dir, "70kb_emoji_rt.txt")
        emoji_char = "🎉"
        char_count = (70 * 1024) // len(emoji_char.encode("utf-8"))
        content = emoji_char * char_count
        save_file(content, filepath)
        loaded = load_file(filepath)
        assert loaded == content

    def test_roundtrip_cjk_large(self, tmp_dir):
        """Large CJK content survives a save/load round-trip."""
        filepath = os.path.join(tmp_dir, "cjk_rt.txt")
        # CJK characters are 3 bytes each in UTF-8
        cjk_segment = "你好世界测试数据"
        repeat_count = (80 * 1024) // len(cjk_segment.encode("utf-8"))
        content = cjk_segment * repeat_count
        byte_len = len(content.encode("utf-8"))
        assert byte_len > BUFFER_SIZE
        save_file(content, filepath)
        loaded = load_file(filepath)
        assert loaded == content


class TestLoadFile:
    """Tests for load_file function."""

    def test_load_nonexistent_file(self):
        """Loading a nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_file("/nonexistent/path/file.txt")
