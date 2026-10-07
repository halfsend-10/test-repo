"""Tests for file_saver module.

Covers buffer-boundary behaviour with multibyte UTF-8 characters to
prevent regressions on the segfault fixed in issue #1105.
"""

import os
import tempfile

from file_saver import BUFFER_SIZE, _find_safe_boundary, save_file


def _roundtrip(content: str) -> str:
    """Save content to a temp file and read it back."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    finally:
        os.unlink(path)


class TestSaveFileSmall:
    """Files under the 64KB buffer boundary."""

    def test_ascii_under_boundary(self):
        content = "a" * (BUFFER_SIZE - 1)
        assert _roundtrip(content) == content

    def test_multibyte_under_boundary(self):
        # Each emoji is 4 bytes; stay under 64KB in byte length
        content = "\U0001f600" * (BUFFER_SIZE // 4 - 1)
        assert _roundtrip(content) == content


class TestSaveFileOverBoundary:
    """Files exceeding the 64KB buffer boundary."""

    def test_ascii_over_boundary(self):
        content = "x" * (BUFFER_SIZE + 1024)
        assert _roundtrip(content) == content

    def test_multibyte_over_boundary(self):
        """This is the crash scenario from issue #1105."""
        # ~70KB of emoji (4 bytes each)
        content = "\U0001f600" * (70 * 1024 // 4)
        assert _roundtrip(content) == content

    def test_multibyte_at_exact_boundary(self):
        """Multibyte character spanning the exact 64KB boundary."""
        # Fill up to 1 byte before the boundary with ASCII, then add
        # a 4-byte emoji that straddles the boundary.
        content = "a" * (BUFFER_SIZE - 1) + "\U0001f600"
        assert _roundtrip(content) == content

    def test_large_mixed_content(self):
        """1MB+ file with mixed ASCII and multibyte content."""
        block = "Hello \U0001f30d world 世界 " * 100
        content = block * (1024 * 1024 // len(block.encode("utf-8")) + 1)
        assert len(content.encode("utf-8")) > 1024 * 1024
        assert _roundtrip(content) == content

    def test_cjk_over_boundary(self):
        """CJK characters (3 bytes each) crossing the boundary."""
        content = "世" * (BUFFER_SIZE // 3 + 1000)
        assert _roundtrip(content) == content


class TestFindSafeBoundary:
    """Unit tests for the UTF-8 boundary finder."""

    def test_ascii_boundary(self):
        data = b"abcdef"
        assert _find_safe_boundary(data, 3) == 3

    def test_mid_multibyte(self):
        # \U0001f600 encodes as f0 9f 98 80
        data = "a\U0001f600b".encode("utf-8")
        # data = b'a' + b'\xf0\x9f\x98\x80' + b'b'
        # Positions: 0=a, 1=f0, 2=9f, 3=98, 4=80, 5=b
        # Splitting at pos 3 (continuation byte) should back up to pos 1
        assert _find_safe_boundary(data, 3) == 1

    def test_boundary_at_char_start(self):
        data = "ab\U0001f600".encode("utf-8")
        # pos 2 is the start of the 4-byte sequence (0xf0), not a
        # continuation byte, so it stays at 2
        assert _find_safe_boundary(data, 2) == 2

    def test_empty_data(self):
        data = b""
        assert _find_safe_boundary(data, 0) == 0
