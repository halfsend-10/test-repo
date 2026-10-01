"""Tests for the file_saver module.

Covers saving large files with multibyte UTF-8 characters, verifying
that buffer calculations use byte length and that content survives
a round-trip through save/load.
"""

import os
import tempfile

import pytest

from src.file_saver import BUFFER_SIZE, _calculate_byte_length, load_file, save_file


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


class TestCalculateByteLength:
    def test_ascii_string(self):
        assert _calculate_byte_length("hello") == 5

    def test_multibyte_emoji(self):
        # Each emoji is 4 bytes in UTF-8
        assert _calculate_byte_length("\U0001f600") == 4

    def test_cjk_characters(self):
        # CJK characters are 3 bytes each in UTF-8
        assert _calculate_byte_length("世界") == 6

    def test_empty_string(self):
        assert _calculate_byte_length("") == 0


class TestSaveFileWithLargeMultibyteContent:
    """Test saving files larger than 64KB with multibyte UTF-8 characters."""

    def test_large_file_with_emoji(self, tmp_dir):
        """70KB of emoji characters should save and load correctly."""
        # Each emoji is 4 bytes; we need > 64KB = 65536 bytes
        # 70KB ~ 71680 bytes => need ~17920 emoji characters
        emoji_count = 71680 // 4
        content = "\U0001f600" * emoji_count
        byte_size = len(content.encode("utf-8"))
        assert byte_size >= 70000

        path = str(tmp_dir / "emoji_large.txt")
        save_file(path, content)
        loaded = load_file(path)
        assert loaded == content

    def test_large_ascii_file(self, tmp_dir):
        """70KB ASCII-only file should save correctly (baseline)."""
        content = "A" * 71680
        path = str(tmp_dir / "ascii_large.txt")
        save_file(path, content)
        loaded = load_file(path)
        assert loaded == content

    def test_just_under_64kb_with_multibyte(self, tmp_dir):
        """File just under 64KB with multibyte characters should save."""
        # 3-byte CJK characters, just under 64KB
        char_count = (BUFFER_SIZE - 10) // 3
        content = "世" * char_count
        byte_size = len(content.encode("utf-8"))
        assert byte_size < BUFFER_SIZE

        path = str(tmp_dir / "under_64kb.txt")
        save_file(path, content)
        loaded = load_file(path)
        assert loaded == content

    def test_multibyte_straddling_buffer_boundary(self, tmp_dir):
        """A multibyte character at the 64KB byte boundary should save."""
        # Fill with ASCII up to just before the boundary, then add emoji
        ascii_prefix = "A" * (BUFFER_SIZE - 2)
        # Emoji is 4 bytes and straddles the 64KB boundary
        content = ascii_prefix + "\U0001f600" * 100
        byte_size = len(content.encode("utf-8"))
        assert byte_size > BUFFER_SIZE

        path = str(tmp_dir / "straddling.txt")
        save_file(path, content)
        loaded = load_file(path)
        assert loaded == content

    def test_64k_emoji_characters(self, tmp_dir):
        """64K emoji characters (~256KB bytes) should save correctly."""
        content = "\U0001f600" * 65536
        byte_size = len(content.encode("utf-8"))
        assert byte_size == 65536 * 4  # 256KB

        path = str(tmp_dir / "many_emoji.txt")
        save_file(path, content)
        loaded = load_file(path)
        assert loaded == content


class TestSaveFileEdgeCases:
    def test_empty_file(self, tmp_dir):
        path = str(tmp_dir / "empty.txt")
        save_file(path, "")
        loaded = load_file(path)
        assert loaded == ""

    def test_single_character(self, tmp_dir):
        path = str(tmp_dir / "single.txt")
        save_file(path, "x")
        loaded = load_file(path)
        assert loaded == "x"

    def test_exactly_64kb_ascii(self, tmp_dir):
        """File of exactly 64KB (buffer size boundary) should save."""
        content = "B" * BUFFER_SIZE
        path = str(tmp_dir / "exact_64kb.txt")
        save_file(path, content)
        loaded = load_file(path)
        assert loaded == content

    def test_mixed_ascii_and_multibyte(self, tmp_dir):
        """Mixed content crossing the buffer boundary should save."""
        # Alternate ASCII and emoji to create mixed-byte-width content
        chunk = "Hello \U0001f600 World 世界 "
        repeat_count = BUFFER_SIZE // len(chunk.encode("utf-8")) + 100
        content = chunk * repeat_count
        assert len(content.encode("utf-8")) > BUFFER_SIZE

        path = str(tmp_dir / "mixed.txt")
        save_file(path, content)
        loaded = load_file(path)
        assert loaded == content
