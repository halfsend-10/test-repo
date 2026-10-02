"""Tests for the file handler module.

Verifies correct saving of files with multibyte UTF-8 content at and
around the 64KB buffer boundary — the regression scenario from issue
#1737.
"""

import os
import tempfile

import pytest

from src.file_handler import BUFFER_SIZE, save_file


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestSaveFile:
    """Tests for save_file boundary behavior."""

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

    def test_save_exact_buffer_boundary(self, tmp_dir):
        """Save content whose UTF-8 encoding is exactly BUFFER_SIZE bytes.

        Off-by-one risk point: content lands exactly on the chunk
        boundary. The loop must handle this without an extra empty
        write or short count.
        """
        filepath = os.path.join(tmp_dir, "exact_boundary.txt")
        # 'a' is 1 byte in UTF-8; BUFFER_SIZE 'a's = exactly BUFFER_SIZE bytes
        content = "a" * BUFFER_SIZE
        byte_len = len(content.encode("utf-8"))
        assert byte_len == BUFFER_SIZE
        bytes_written = save_file(content, filepath)
        assert bytes_written == byte_len

    def test_save_buffer_boundary_plus_one(self, tmp_dir):
        """Save content whose UTF-8 encoding is BUFFER_SIZE + 1 bytes.

        Verifies the second chunk is written correctly when it contains
        a single byte.
        """
        filepath = os.path.join(tmp_dir, "boundary_plus_one.txt")
        content = "a" * (BUFFER_SIZE + 1)
        byte_len = len(content.encode("utf-8"))
        assert byte_len == BUFFER_SIZE + 1
        bytes_written = save_file(content, filepath)
        assert bytes_written == byte_len

    def test_save_70kb_utf8_file(self, tmp_dir):
        """Save ~70KB file with emoji characters (over buffer boundary).

        This is the primary regression test for the segfault reported in
        issue #1737. Previously, the buffer was allocated using character
        count instead of byte length, causing a buffer overflow when
        multibyte characters pushed the actual byte count past 64KB.
        """
        filepath = os.path.join(tmp_dir, "70kb_utf8.txt")
        # Each emoji is 4 bytes in UTF-8; build ~70KB of emoji content
        emoji_char = "\U0001f389"
        char_count = (70 * 1024) // len(emoji_char.encode("utf-8"))
        content = emoji_char * char_count
        byte_len = len(content.encode("utf-8"))
        assert byte_len > BUFFER_SIZE, "Test content must exceed buffer size"
        bytes_written = save_file(content, filepath)
        assert bytes_written == byte_len


class TestRoundTrip:
    """Round-trip integrity at the buffer boundary."""

    def test_roundtrip_70kb_emoji(self, tmp_dir):
        """70KB emoji content survives a save round-trip byte-for-byte.

        Verifies that saved content matches original after reload, ensuring
        no truncation or corruption at buffer boundaries.
        """
        filepath = os.path.join(tmp_dir, "70kb_emoji_rt.txt")
        emoji_char = "\U0001f389"
        char_count = (70 * 1024) // len(emoji_char.encode("utf-8"))
        content = emoji_char * char_count
        save_file(content, filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            loaded = f.read()
        assert loaded == content
