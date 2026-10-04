"""Tests for the file_saver module.

Covers the bug described in issue #1794: saving files larger than 64KB
containing UTF-8 multibyte characters caused a crash because the chunked
write logic could split multibyte sequences at chunk boundaries.
"""

import os
import tempfile

import pytest

from src.file_saver import CHUNK_SIZE, _find_safe_split, load_file, save_file


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestFindSafeSplit:
    """Unit tests for the internal _find_safe_split helper."""

    def test_split_within_ascii(self):
        data = b"Hello, world!"
        assert _find_safe_split(data, 5) == 5

    def test_split_at_end(self):
        data = b"short"
        assert _find_safe_split(data, 100) == 5

    def test_split_before_2byte_char(self):
        # 'é' is 2 bytes: \xc3\xa9
        data = b"aaaa\xc3\xa9bb"
        # Splitting at 5 lands on \xa9 (continuation), should back up to 4.
        assert _find_safe_split(data, 5) == 4

    def test_split_before_3byte_char(self):
        # '€' is 3 bytes: \xe2\x82\xac
        data = b"aaa\xe2\x82\xacbb"
        # Splitting at 4 lands on first continuation byte, back up to 3.
        assert _find_safe_split(data, 4) == 3
        # Splitting at 5 lands on second continuation byte, back up to 3.
        assert _find_safe_split(data, 5) == 3

    def test_split_before_4byte_char(self):
        # '😀' is 4 bytes: \xf0\x9f\x98\x80
        data = b"aa\xf0\x9f\x98\x80bb"
        # Splitting at 3, 4, or 5 should all back up to 2.
        assert _find_safe_split(data, 3) == 2
        assert _find_safe_split(data, 4) == 2
        assert _find_safe_split(data, 5) == 2

    def test_split_after_complete_char(self):
        # Splitting right after a complete multibyte char is fine.
        data = b"aa\xc3\xa9bb"  # 'aaébb'
        assert _find_safe_split(data, 4) == 4  # after 'é'


class TestSaveFile:
    """Integration tests for save_file."""

    def test_save_and_load_ascii(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        content = "Hello, world!"
        save_file(path, content)
        assert load_file(path) == content

    def test_save_small_utf8(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.txt")
        content = "Hello 🌍🌎🌏 世界"
        save_file(path, content)
        assert load_file(path) == content

    def test_save_large_ascii_file(self, tmp_dir):
        """Control case: large ASCII file should save correctly."""
        path = os.path.join(tmp_dir, "large_ascii.txt")
        content = "A" * (CHUNK_SIZE + 1024)
        save_file(path, content)
        assert load_file(path) == content

    def test_save_70kb_with_emoji(self, tmp_dir):
        """Reproduce issue #1794: 70KB file with emoji should save without crash."""
        path = os.path.join(tmp_dir, "emoji.txt")
        # Build a ~70KB string containing emoji throughout.
        emoji_block = "Hello 😀🎉🚀 "  # 18 bytes in UTF-8
        repeat_count = (70 * 1024) // len(emoji_block.encode("utf-8")) + 1
        content = emoji_block * repeat_count
        assert len(content.encode("utf-8")) > 70 * 1024

        save_file(path, content)
        assert load_file(path) == content

    def test_save_utf8_spanning_chunk_boundary(self, tmp_dir):
        """Key regression test: a 4-byte UTF-8 char spans the 65536th byte offset."""
        path = os.path.join(tmp_dir, "boundary.txt")
        # Place a 4-byte emoji exactly at the chunk boundary.
        # Fill up to CHUNK_SIZE - 2 with ASCII, then a 4-byte char
        # crosses the boundary.
        prefix = "x" * (CHUNK_SIZE - 2)
        boundary_char = "😀"  # 4 bytes
        suffix = "y" * 1000
        content = prefix + boundary_char + suffix

        encoded = content.encode("utf-8")
        # Verify the emoji actually spans the 64KB boundary.
        assert encoded[CHUNK_SIZE - 2] == 0xF0  # start of 4-byte seq
        assert CHUNK_SIZE - 2 + 4 > CHUNK_SIZE  # extends past boundary

        save_file(path, content)
        assert load_file(path) == content

    def test_save_cjk_large_file(self, tmp_dir):
        """Large file with CJK characters (3-byte UTF-8 sequences)."""
        path = os.path.join(tmp_dir, "cjk.txt")
        cjk_block = "你好世界测试文字"  # 8 CJK chars, 24 bytes
        repeat_count = (70 * 1024) // len(cjk_block.encode("utf-8")) + 1
        content = cjk_block * repeat_count
        assert len(content.encode("utf-8")) > 70 * 1024

        save_file(path, content)
        assert load_file(path) == content

    def test_atomic_write_no_partial_file(self, tmp_dir):
        """If save fails, no partial file should remain at the target path."""
        path = os.path.join(tmp_dir, "no_exist_dir", "sub", "test.txt")
        with pytest.raises(FileNotFoundError):
            save_file(path, "test")
        assert not os.path.exists(path)

    def test_custom_chunk_size(self, tmp_dir):
        """Verify correct behavior with a smaller chunk size."""
        path = os.path.join(tmp_dir, "small_chunk.txt")
        content = "Hello 😀 World 🌍 Test 🎉" * 100
        save_file(path, content, chunk_size=32)
        assert load_file(path) == content
