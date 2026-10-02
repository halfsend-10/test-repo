"""Tests for the buffered file writer with UTF-8-safe chunking."""

import os
import tempfile

from src.file_writer import CHUNK_SIZE, _utf8_safe_boundary, save_file


class TestUtf8SafeBoundary:
    """Unit tests for _utf8_safe_boundary."""

    def test_ascii_boundary(self):
        """ASCII bytes are single-byte — any boundary is safe."""
        data = b"abcdefgh"
        assert _utf8_safe_boundary(data, 4) == 4

    def test_boundary_between_multibyte_chars(self):
        """Boundary that falls between two complete characters."""
        # Two 3-byte CJK characters: U+4E16 (世) = E4 B8 96,
        # U+754C (界) = E7 95 8C
        data = "世界".encode("utf-8")  # 6 bytes total
        assert _utf8_safe_boundary(data, 3) == 3

    def test_boundary_splits_2byte_char(self):
        """Boundary inside a 2-byte character backs up."""
        # U+00E9 (é) = C3 A9 (2 bytes)
        data = b"a" + "é".encode("utf-8")  # b'a\xc3\xa9'
        # Boundary at 2 lands on the continuation byte 0xA9.
        assert _utf8_safe_boundary(data, 2) == 1

    def test_boundary_splits_3byte_char(self):
        """Boundary inside a 3-byte character backs up."""
        # U+4E16 (世) = E4 B8 96
        data = b"a" + "世".encode("utf-8")  # b'a\xe4\xb8\x96'
        # Boundary at 2 lands inside the character.
        assert _utf8_safe_boundary(data, 2) == 1
        # Boundary at 3 also lands inside (on the last cont. byte).
        assert _utf8_safe_boundary(data, 3) == 1

    def test_boundary_splits_4byte_char(self):
        """Boundary inside a 4-byte emoji backs up."""
        # U+1F600 (😀) = F0 9F 98 80
        data = b"a" + "😀".encode("utf-8")  # b'a\xf0\x9f\x98\x80'
        assert _utf8_safe_boundary(data, 2) == 1
        assert _utf8_safe_boundary(data, 3) == 1
        assert _utf8_safe_boundary(data, 4) == 1

    def test_boundary_at_end(self):
        """Boundary at or past end returns len(data)."""
        data = b"hello"
        assert _utf8_safe_boundary(data, 5) == 5
        assert _utf8_safe_boundary(data, 100) == 5

    def test_boundary_at_zero(self):
        """Boundary at 0 returns 0 (empty first chunk)."""
        data = "😀".encode("utf-8")
        assert _utf8_safe_boundary(data, 0) == 0


class TestSaveFile:
    """Integration tests for save_file."""

    def _round_trip(self, content: str) -> str:
        """Save content via save_file, read it back, return the result."""
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".txt"
        ) as tmp:
            path = tmp.name
        try:
            save_file(content, path)
            with open(path, "rb") as fh:
                return fh.read().decode("utf-8")
        finally:
            os.unlink(path)

    def test_small_ascii_file(self):
        """Files under CHUNK_SIZE with ASCII are unchanged."""
        content = "Hello, world!"
        assert self._round_trip(content) == content

    def test_small_multibyte_file(self):
        """Files under CHUNK_SIZE with multibyte chars are unchanged."""
        content = "Hello 🌍🌎🌏 World!"
        assert self._round_trip(content) == content

    def test_large_ascii_file(self):
        """Files over CHUNK_SIZE with ASCII only are unchanged."""
        content = "A" * (CHUNK_SIZE + 1000)
        assert self._round_trip(content) == content

    def test_large_file_with_emoji(self):
        """~70KB of emoji (4-byte chars) round-trips correctly.

        This is the primary reproduction case from the bug report.
        """
        # U+1F600 is 4 bytes in UTF-8. 70KB / 4 = 17920 characters.
        content = "😀" * 17920
        assert self._round_trip(content) == content

    def test_emoji_at_exact_chunk_boundary(self):
        """4-byte emoji placed so it straddles byte 65536."""
        # Fill with ASCII up to 2 bytes before the boundary, then a
        # 4-byte emoji that would start at 65534 and end at 65538.
        prefix = "A" * (CHUNK_SIZE - 2)
        content = prefix + "😀" + "B" * 100
        assert self._round_trip(content) == content

    def test_cjk_at_chunk_boundary(self):
        """3-byte CJK character at the 64KB boundary."""
        # U+4E16 (世) is 3 bytes. 65536 / 3 = 21845 chars + 1 byte.
        # After 21845 chars (65535 bytes), the next char starts at
        # byte 65535 and would end at 65538, straddling the boundary.
        content = "世" * 21846 + "A" * 100
        assert self._round_trip(content) == content

    def test_file_just_under_boundary(self):
        """File of exactly 65535 bytes (just under 64KB) — control."""
        content = "A" * 65535
        assert self._round_trip(content) == content

    def test_exact_chunk_size_file(self):
        """File of exactly CHUNK_SIZE bytes."""
        content = "A" * CHUNK_SIZE
        assert self._round_trip(content) == content

    def test_empty_file(self):
        """Empty content produces an empty file."""
        assert self._round_trip("") == ""
