"""Tests for save_handler — UTF-8 aware chunked file saving."""

import os
import tempfile

import save_handler
from save_handler import BUFFER_SIZE, _adjust_for_utf8_boundary, save_file


class TestAdjustForUtf8Boundary:
    """Unit tests for the UTF-8 boundary adjustment helper."""

    def test_ascii_boundary_unchanged(self):
        """Position inside pure ASCII data should not move."""
        data = b"hello world"
        assert _adjust_for_utf8_boundary(data, 5) == 5

    def test_on_continuation_byte_moves_back(self):
        # U+00E9 'é' is 0xC3 0xA9 in UTF-8 (2-byte sequence)
        data = b"aaa" + "é".encode("utf-8")  # b'aaa\xc3\xa9'
        # Position 4 is the continuation byte 0xA9
        assert _adjust_for_utf8_boundary(data, 4) == 3

    def test_on_leading_byte_unchanged(self):
        data = b"aaa" + "é".encode("utf-8")
        # Position 3 is the leading byte 0xC3
        assert _adjust_for_utf8_boundary(data, 3) == 3

    def test_four_byte_char_continuation(self):
        # U+1F600 '😀' is 0xF0 0x9F 0x98 0x80 (4-byte sequence)
        data = b"xyz" + "😀".encode("utf-8")
        # Positions 4, 5, 6 are continuation bytes
        assert _adjust_for_utf8_boundary(data, 6) == 3
        assert _adjust_for_utf8_boundary(data, 5) == 3
        assert _adjust_for_utf8_boundary(data, 4) == 3

    def test_three_byte_char_continuation(self):
        # U+4E16 '世' is 0xE4 0xB8 0x96 (3-byte sequence)
        data = b"ab" + "世".encode("utf-8")
        assert _adjust_for_utf8_boundary(data, 4) == 2
        assert _adjust_for_utf8_boundary(data, 3) == 2


class TestSaveFile:
    """Integration tests for save_file."""

    def test_save_small_ascii_file(self, tmp_path):
        """Files smaller than the buffer should save correctly."""
        path = str(tmp_path / "small.txt")
        content = "Hello, world!\n"
        save_file(content, path)
        assert open(path, "r", encoding="utf-8").read() == content

    def test_save_small_utf8_file(self, tmp_path):
        """Small files with multibyte characters should round-trip."""
        path = str(tmp_path / "small_utf8.txt")
        content = "Héllo 世界 😀\n"
        save_file(content, path)
        assert open(path, "r", encoding="utf-8").read() == content

    def test_save_large_ascii_file(self, tmp_path):
        """Files larger than 64KB with only ASCII should save."""
        path = str(tmp_path / "large_ascii.txt")
        content = "A" * (BUFFER_SIZE + 1024)
        save_file(content, path)
        assert open(path, "r", encoding="utf-8").read() == content

    def test_save_large_utf8_file_round_trip(self, tmp_path):
        """Files >64KB with multibyte characters must round-trip."""
        path = str(tmp_path / "large_utf8.txt")
        # Build ~70KB of mixed ASCII + emoji
        unit = "Hello 😀 世界! "
        content = unit * (70 * 1024 // len(unit.encode("utf-8")) + 1)
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content

    def test_multibyte_at_exact_buffer_boundary(self, tmp_path):
        """A multibyte char straddling the 64KB boundary must not be
        split."""
        path = str(tmp_path / "boundary.txt")
        # Place a 4-byte emoji exactly so it straddles the boundary:
        # BUFFER_SIZE - 1 bytes of ASCII, then a 4-byte emoji.
        padding = "A" * (BUFFER_SIZE - 1)
        content = padding + "😀" + "B" * 100
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content

    def test_multibyte_at_boundary_minus_one(self, tmp_path):
        """A multibyte char ending exactly at the boundary is fine."""
        path = str(tmp_path / "boundary_m1.txt")
        # 2-byte char ending at position BUFFER_SIZE
        padding = "A" * (BUFFER_SIZE - 2)
        content = padding + "é" + "B" * 100
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content

    def test_three_byte_char_at_boundary(self, tmp_path):
        """3-byte CJK character straddling the boundary."""
        path = str(tmp_path / "cjk_boundary.txt")
        padding = "A" * (BUFFER_SIZE - 1)
        content = padding + "世" + "B" * 100
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content

    def test_exactly_buffer_size_ascii(self, tmp_path):
        """File whose size equals the buffer exactly."""
        path = str(tmp_path / "exact.txt")
        content = "X" * BUFFER_SIZE
        save_file(content, path)
        result = open(path, "r", encoding="utf-8").read()
        assert result == content

    def test_empty_file(self, tmp_path):
        """Empty content should produce an empty file."""
        path = str(tmp_path / "empty.txt")
        save_file("", path)
        assert open(path, "r", encoding="utf-8").read() == ""

    def test_tmp_file_cleaned_on_error(self, tmp_path):
        """The .tmp file should not remain if writing fails."""
        path = str(tmp_path / "nonexistent_dir" / "fail.txt")
        try:
            save_file("data", path)
        except OSError:
            pass
        assert not os.path.exists(path + ".tmp")
