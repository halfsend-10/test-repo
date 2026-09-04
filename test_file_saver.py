"""Tests for file_saver module.

Verifies correct handling of UTF-8 multibyte characters in files
of various sizes, including the >64KB threshold that triggered the
segfault in v2.3.1.
"""

import os
import tempfile

from file_saver import calculate_buffer_size, save_file


class TestCalculateBufferSize:
    """Tests for calculate_buffer_size using byte length."""

    def test_ascii_content(self):
        content = "hello"
        assert calculate_buffer_size(content) == 5

    def test_multibyte_emoji(self):
        # Each emoji is 4 bytes in UTF-8
        content = "\U0001f600"  # 😀
        assert calculate_buffer_size(content) == 4

    def test_cjk_characters(self):
        # CJK characters are 3 bytes each in UTF-8
        content = "世界"  # 世界
        assert calculate_buffer_size(content) == 6

    def test_mixed_content(self):
        # 'a' = 1 byte, '€' = 3 bytes, '😀' = 4 bytes
        content = "a€\U0001f600"
        assert calculate_buffer_size(content) == 8


class TestSaveFile:
    """Tests for save_file with various content sizes and encodings."""

    def test_save_large_file_with_emoji(self):
        """Save a >64KB file containing emoji — the exact crash scenario."""
        # Each emoji is 4 bytes; 20000 emojis = 80KB > 64KB threshold
        content = "\U0001f600" * 20000
        assert len(content.encode("utf-8")) > 65536

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name

        try:
            save_file(content, path)
            with open(path, "rb") as f:
                saved = f.read()
            assert saved == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_save_exactly_64kb_multibyte(self):
        """Save exactly 64KB of multibyte content."""
        # 3-byte CJK chars: 21846 chars * 3 = 65538 bytes (just over 64KB)
        content = "世" * 21846
        byte_len = len(content.encode("utf-8"))
        assert byte_len >= 65536

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name

        try:
            save_file(content, path)
            with open(path, "rb") as f:
                saved = f.read()
            assert saved == content.encode("utf-8")
            assert len(saved) == byte_len
        finally:
            os.unlink(path)

    def test_save_large_mixed_ascii_and_multibyte(self):
        """Save a large file mixing ASCII and multibyte characters."""
        # Mix ASCII and emoji to exceed 64KB
        chunk = "hello \U0001f600 world 世界 "  # 20 bytes
        repeat = 65536 // len(chunk.encode("utf-8")) + 1
        content = chunk * repeat
        assert len(content.encode("utf-8")) > 65536

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name

        try:
            save_file(content, path)
            with open(path, "rb") as f:
                saved = f.read()
            assert saved == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_save_small_file_with_multibyte(self):
        """Regression guard: files under 64KB with multibyte chars still work."""
        content = "\U0001f600" * 100  # 400 bytes, well under 64KB
        assert len(content.encode("utf-8")) < 65536

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name

        try:
            save_file(content, path)
            with open(path, "rb") as f:
                saved = f.read()
            assert saved == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_save_large_ascii_only(self):
        """Large ASCII-only files should continue to work."""
        content = "a" * 100000  # 100KB of ASCII
        assert len(content.encode("utf-8")) > 65536

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name

        try:
            save_file(content, path)
            with open(path, "rb") as f:
                saved = f.read()
            assert saved == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_save_empty_file(self):
        """Empty content should save without error."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name

        try:
            save_file("", path)
            with open(path, "rb") as f:
                saved = f.read()
            assert saved == b""
        finally:
            os.unlink(path)
