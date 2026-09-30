"""Tests for file_saver module.

Covers the UTF-8 multibyte buffer overflow fix described in issue #1662:
- Files at and above 64KB with multibyte UTF-8 characters save correctly
- Multibyte characters straddling the 64KB byte boundary are handled
- Content round-trips without corruption
"""

import os
import tempfile

import pytest

from src.file_saver import (
    DEFAULT_BUFFER_SIZE,
    _calculate_chunk_boundary,
    save_file,
)


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory, cleaned up after each test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestSaveFileUTF8:
    """Tests for save_file with UTF-8 multibyte content."""

    def test_save_ascii_under_64kb(self, tmp_dir):
        """ASCII content under 64KB saves without issue."""
        path = os.path.join(tmp_dir, "small_ascii.txt")
        content = "a" * (DEFAULT_BUFFER_SIZE - 1)
        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_ascii_over_64kb(self, tmp_dir):
        """ASCII content over 64KB saves correctly."""
        path = os.path.join(tmp_dir, "large_ascii.txt")
        content = "a" * (DEFAULT_BUFFER_SIZE + 1024)
        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_emoji_at_64kb(self, tmp_dir):
        """64KB of emoji-only content saves correctly."""
        path = os.path.join(tmp_dir, "emoji_64kb.txt")
        # Each emoji is 4 bytes in UTF-8; fill to ~64KB
        emoji_count = DEFAULT_BUFFER_SIZE // 4
        content = "\U0001f600" * emoji_count
        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_emoji_over_64kb(self, tmp_dir):
        """65KB+ of emoji-only content saves correctly (was crashing)."""
        path = os.path.join(tmp_dir, "emoji_over_64kb.txt")
        # Create content whose byte length exceeds 64KB
        emoji_count = (DEFAULT_BUFFER_SIZE + 4096) // 4
        content = "\U0001f600" * emoji_count
        encoded_len = len(content.encode("utf-8"))
        assert encoded_len > DEFAULT_BUFFER_SIZE

        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_save_mixed_ascii_multibyte_128kb(self, tmp_dir):
        """128KB of mixed ASCII and multibyte content saves correctly."""
        path = os.path.join(tmp_dir, "mixed_128kb.txt")
        # Mix ASCII and CJK characters (3 bytes each in UTF-8)
        unit = "Hello 世界 "  # "Hello 世界 "
        target_bytes = DEFAULT_BUFFER_SIZE * 2
        repeats = target_bytes // len(unit.encode("utf-8")) + 1
        content = unit * repeats
        assert len(content.encode("utf-8")) >= target_bytes

        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_multibyte_char_at_buffer_boundary(self, tmp_dir):
        """Multibyte character straddling the 64KB byte boundary is handled."""
        path = os.path.join(tmp_dir, "boundary.txt")
        # Fill with ASCII up to 2 bytes before the boundary, then add
        # a 4-byte emoji that would straddle the 64KB mark
        padding = "x" * (DEFAULT_BUFFER_SIZE - 2)
        content = padding + "\U0001f600" + "after"
        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            result = f.read()
        assert result == content

    def test_cjk_content_over_64kb(self, tmp_dir):
        """CJK characters (3 bytes each) over 64KB save correctly."""
        path = os.path.join(tmp_dir, "cjk.txt")
        # CJK characters are 3 bytes in UTF-8
        char_count = (DEFAULT_BUFFER_SIZE + 2048) // 3
        content = "世" * char_count
        assert len(content.encode("utf-8")) > DEFAULT_BUFFER_SIZE

        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == content

    def test_empty_content(self, tmp_dir):
        """Empty string saves as an empty file."""
        path = os.path.join(tmp_dir, "empty.txt")
        save_file(path, "")

        with open(path, "r", encoding="utf-8") as f:
            assert f.read() == ""

    def test_content_type_validation(self, tmp_dir):
        """Non-string content raises TypeError."""
        path = os.path.join(tmp_dir, "invalid.txt")
        with pytest.raises(TypeError, match="content must be a string"):
            save_file(path, b"bytes")

    def test_file_content_integrity(self, tmp_dir):
        """File round-trips preserve exact byte content."""
        path = os.path.join(tmp_dir, "integrity.txt")
        # Mix of 1-byte, 2-byte, 3-byte, and 4-byte UTF-8 characters
        content = (
            "ASCII "
            "éèê "        # 2-byte (accented Latin)
            "世界こ "          # 3-byte (CJK + Hiragana)
            "\U0001f600\U0001f4a9 "         # 4-byte (emoji)
        ) * 5000

        save_file(path, content)

        with open(path, "rb") as f:
            raw = f.read()
        assert raw == content.encode("utf-8")


class TestCalculateChunkBoundary:
    """Tests for the chunk boundary calculation helper."""

    def test_ascii_within_buffer(self):
        """ASCII string within buffer returns full length."""
        content = "hello"
        result = _calculate_chunk_boundary(content, 0, 10)
        assert result == 5

    def test_multibyte_respects_boundary(self):
        """Multibyte chars that would exceed buffer are excluded."""
        # 4-byte emoji; buffer_size=6 fits only 1 emoji (4 bytes)
        content = "\U0001f600\U0001f600"
        result = _calculate_chunk_boundary(content, 0, 6)
        assert result == 1

    def test_exact_fit(self):
        """Characters that exactly fill the buffer are included."""
        content = "\U0001f600\U0001f600"  # 8 bytes total
        result = _calculate_chunk_boundary(content, 0, 8)
        assert result == 2

    def test_start_offset(self):
        """char_start parameter correctly offsets the scan."""
        content = "ab\U0001f600\U0001f600"
        result = _calculate_chunk_boundary(content, 2, 4)
        assert result == 3  # one emoji fits in 4 bytes
