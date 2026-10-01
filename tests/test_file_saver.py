"""Tests for the chunked file saver with UTF-8 boundary handling."""

import os
import tempfile

from src.file_saver import DEFAULT_CHUNK_SIZE, _find_safe_split, save_file


class TestFindSafeSplit:
    """Unit tests for _find_safe_split."""

    def test_ascii_only(self):
        data = b"abcdefgh"
        assert _find_safe_split(data, 4) == 4

    def test_split_before_multibyte(self):
        # 'é' is 0xC3 0xA9 (2 bytes). Place it so the boundary falls
        # between its two bytes.
        prefix = b"a" * 3  # 3 bytes
        char = "é".encode("utf-8")  # 2 bytes
        data = prefix + char + b"z"
        # max_size=4 lands on the continuation byte 0xA9.
        assert _find_safe_split(data, 4) == 3

    def test_split_on_leading_byte(self):
        prefix = b"a" * 4
        char = "é".encode("utf-8")
        data = prefix + char
        # max_size=4 lands on 'a' (ASCII), safe as-is.
        assert _find_safe_split(data, 4) == 4

    def test_four_byte_char_boundary(self):
        # U+1F600 (😀) encodes as 4 bytes: F0 9F 98 80
        prefix = b"a" * 2
        emoji = "😀".encode("utf-8")
        data = prefix + emoji + b"end"
        # max_size=4 lands on the 3rd byte of the emoji (continuation).
        assert _find_safe_split(data, 4) == 2

    def test_max_size_beyond_data(self):
        data = b"hello"
        assert _find_safe_split(data, 100) == 5


class TestSaveFile:
    """Integration tests for save_file."""

    def _roundtrip(self, content, chunk_size=DEFAULT_CHUNK_SIZE):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            nbytes = save_file(content, path, chunk_size=chunk_size)
            assert nbytes == len(content.encode("utf-8"))
            with open(path, "rb") as fh:
                raw = fh.read()
            assert raw.decode("utf-8") == content
        finally:
            os.unlink(path)

    def test_small_ascii_file(self):
        self._roundtrip("Hello, world!\n")

    def test_file_under_64kb_with_emoji(self):
        # 63 KB of emoji content — should save without issue.
        content = "😀" * (63 * 1024 // 4)
        self._roundtrip(content)

    def test_file_over_64kb_with_emoji(self):
        # 65 KB of emoji content — the original crash scenario.
        content = "😀" * (65 * 1024 // 4)
        self._roundtrip(content)

    def test_file_128kb_mixed_content(self):
        # 128 KB of mixed ASCII and multibyte content.
        block = "Hello 世界! 🌍 café résumé naïve\n"
        repeats = (128 * 1024) // len(block.encode("utf-8")) + 1
        content = block * repeats
        self._roundtrip(content)

    def test_multibyte_at_exact_boundary(self):
        # Place a 4-byte emoji exactly at byte offset 65535–65538.
        prefix = "a" * (DEFAULT_CHUNK_SIZE - 1)
        content = prefix + "😀" + "tail"
        self._roundtrip(content)

    def test_roundtrip_no_truncation(self):
        # Verify round-trip: saved content matches original.
        content = "日本語テスト\n" * 10000
        self._roundtrip(content)

    def test_small_chunk_size(self):
        # Chunk size smaller than a single multibyte char.
        content = "😀😀😀"
        self._roundtrip(content, chunk_size=3)

    def test_cjk_over_boundary(self):
        # CJK characters (3 bytes each) spanning the 64KB boundary.
        char = "中"  # 3 bytes in UTF-8
        count = (DEFAULT_CHUNK_SIZE // 3) + 10
        content = char * count
        self._roundtrip(content)

    def test_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "dir", "file.txt")
            save_file("test", path)
            with open(path) as fh:
                assert fh.read() == "test"

    def test_empty_content(self):
        self._roundtrip("")
