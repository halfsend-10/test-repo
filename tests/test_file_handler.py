"""Tests for the file handler module.

Verifies correct saving of files with multibyte UTF-8 content at and
around the 64KB buffer boundary, covering 1-byte (ASCII), 3-byte (CJK),
and 4-byte (emoji) characters as well as mixed-encoding content.
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

    def test_save_70kb_utf8_emoji(self, tmp_dir):
        """Save ~70KB file with 4-byte emoji characters (over buffer boundary).

        Emoji are 4 bytes in UTF-8. Since BUFFER_SIZE (65536) mod 4 == 0,
        chunk boundaries align with character boundaries — this verifies
        multi-chunk writes with evenly-aligned multibyte content.
        """
        filepath = os.path.join(tmp_dir, "70kb_utf8.txt")
        emoji_char = "\U0001f389"
        char_count = (70 * 1024) // len(emoji_char.encode("utf-8"))
        content = emoji_char * char_count
        byte_len = len(content.encode("utf-8"))
        assert byte_len > BUFFER_SIZE, "Test content must exceed buffer size"
        bytes_written = save_file(content, filepath)
        assert bytes_written == byte_len

    def test_save_cjk_across_buffer_boundary(self, tmp_dir):
        """Save CJK content whose byte length crosses the buffer boundary.

        CJK characters are 3 bytes in UTF-8. Since BUFFER_SIZE (65536)
        mod 3 == 1, the raw byte stream would split a CJK character
        across chunk boundaries if slicing were character-based. Because
        the implementation encodes first and slices the byte buffer,
        this is safe — but the test confirms no corruption occurs.
        """
        filepath = os.path.join(tmp_dir, "cjk_boundary.txt")
        # U+4E16 (世) is 3 bytes in UTF-8
        cjk_char = "世"
        # Enough characters to exceed BUFFER_SIZE in bytes
        char_count = (BUFFER_SIZE // len(cjk_char.encode("utf-8"))) + 100
        content = cjk_char * char_count
        byte_len = len(content.encode("utf-8"))
        assert byte_len > BUFFER_SIZE, "Test content must exceed buffer size"
        bytes_written = save_file(content, filepath)
        assert bytes_written == byte_len

    def test_save_mixed_ascii_and_multibyte(self, tmp_dir):
        """Save mixed ASCII and multibyte content across the buffer boundary.

        Real-world files contain a mix of ASCII and multibyte characters.
        This test verifies correct handling when byte length differs
        unpredictably from character count due to mixed encoding widths.
        """
        filepath = os.path.join(tmp_dir, "mixed_boundary.txt")
        # Build a repeating pattern: ASCII + CJK + emoji
        pattern = "hello世界\U0001f389"
        pattern_bytes = len(pattern.encode("utf-8"))
        # Repeat enough to cross the buffer boundary
        repeat_count = (BUFFER_SIZE // pattern_bytes) + 10
        content = pattern * repeat_count
        byte_len = len(content.encode("utf-8"))
        assert byte_len > BUFFER_SIZE, "Test content must exceed buffer size"
        bytes_written = save_file(content, filepath)
        assert bytes_written == byte_len


class TestRoundTrip:
    """Round-trip integrity at the buffer boundary."""

    def test_roundtrip_exact_buffer_boundary(self, tmp_dir):
        """Content at exactly BUFFER_SIZE bytes survives a round-trip.

        The exact boundary is the highest-risk off-by-one point.
        Verifies that file content matches the original after reload.
        """
        filepath = os.path.join(tmp_dir, "exact_boundary_rt.txt")
        content = "a" * BUFFER_SIZE
        save_file(content, filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            loaded = f.read()
        assert loaded == content

    def test_roundtrip_buffer_boundary_plus_one(self, tmp_dir):
        """Content at BUFFER_SIZE + 1 bytes survives a round-trip.

        Verifies a single-byte second chunk is written and read correctly.
        """
        filepath = os.path.join(tmp_dir, "boundary_plus_one_rt.txt")
        content = "a" * (BUFFER_SIZE + 1)
        save_file(content, filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            loaded = f.read()
        assert loaded == content

    def test_roundtrip_70kb_emoji(self, tmp_dir):
        """70KB emoji content survives a save–load round-trip byte-for-byte.

        Verifies that saved content matches the original after reload,
        ensuring no truncation or corruption at chunk boundaries.
        """
        filepath = os.path.join(tmp_dir, "70kb_emoji_rt.txt")
        emoji_char = "\U0001f389"
        char_count = (70 * 1024) // len(emoji_char.encode("utf-8"))
        content = emoji_char * char_count
        save_file(content, filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            loaded = f.read()
        assert loaded == content

    def test_roundtrip_cjk_across_boundary(self, tmp_dir):
        """CJK content crossing the buffer boundary survives a round-trip.

        CJK characters are 3 bytes in UTF-8. Since BUFFER_SIZE (65536)
        mod 3 == 1, this exercises unaligned multibyte content at chunk
        boundaries.
        """
        filepath = os.path.join(tmp_dir, "cjk_boundary_rt.txt")
        cjk_char = "世"
        char_count = (BUFFER_SIZE // len(cjk_char.encode("utf-8"))) + 100
        content = cjk_char * char_count
        save_file(content, filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            loaded = f.read()
        assert loaded == content

    def test_roundtrip_mixed_ascii_and_multibyte(self, tmp_dir):
        """Mixed ASCII and multibyte content survives a round-trip.

        Exercises unpredictable byte-vs-character alignment at chunk
        boundaries with real-world-like mixed content.
        """
        filepath = os.path.join(tmp_dir, "mixed_boundary_rt.txt")
        pattern = "hello世界\U0001f389"
        pattern_bytes = len(pattern.encode("utf-8"))
        repeat_count = (BUFFER_SIZE // pattern_bytes) + 10
        content = pattern * repeat_count
        save_file(content, filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            loaded = f.read()
        assert loaded == content
