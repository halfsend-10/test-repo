"""Tests for file_saver — verifying correct UTF-8 buffer handling.

Covers the scenarios from issue #1411:
- 60 KB of emoji text (below chunk boundary)
- 70 KB of emoji text (above chunk boundary — previously crashed)
- 70 KB of ASCII text (control case)
- Content at 64 K chars but >64 KB bytes
- Mixed ASCII + CJK above 64 KB
"""

import os
import tempfile
import unittest

from file_saver import CHUNK_SIZE, save_file


class TestSaveFile(unittest.TestCase):
    """Ensure save_file handles multibyte UTF-8 content of any size."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        for name in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, name))
        os.rmdir(self.tmpdir)

    # -- helpers ----------------------------------------------------------

    def _path(self, name: str) -> str:
        return os.path.join(self.tmpdir, name)

    def _assert_roundtrip(self, content: str, filename: str) -> None:
        path = self._path(filename)
        written = save_file(path, content)
        expected_bytes = len(content.encode("utf-8"))
        self.assertEqual(written, expected_bytes)
        with open(path, "rb") as fh:
            data = fh.read()
        self.assertEqual(len(data), expected_bytes)
        self.assertEqual(data.decode("utf-8"), content)

    # -- test cases from the issue ----------------------------------------

    def test_emoji_below_chunk_boundary(self):
        """60 KB of emoji text — should save successfully."""
        # Each emoji is 4 bytes; 15 000 emojis = 60 000 bytes.
        content = "\U0001F600" * 15_000
        self._assert_roundtrip(content, "emoji_60kb.txt")

    def test_emoji_above_chunk_boundary(self):
        """70 KB of emoji text — previously crashed with segfault."""
        content = "\U0001F600" * 17_500  # 70 000 bytes
        self._assert_roundtrip(content, "emoji_70kb.txt")

    def test_ascii_above_chunk_boundary(self):
        """70 KB of ASCII text — control case, should always work."""
        content = "A" * 70_000
        self._assert_roundtrip(content, "ascii_70kb.txt")

    def test_chars_at_64k_but_bytes_above(self):
        """64 K chars where byte length exceeds 64 KB."""
        # 65 536 two-byte characters = 131 072 bytes > 64 KiB.
        content = "é" * 65_536
        self._assert_roundtrip(content, "chars_64k_bytes_above.txt")

    def test_mixed_ascii_cjk_above_64kb(self):
        """Mixed ASCII + CJK totalling >64 KB."""
        # CJK characters are 3 bytes each in UTF-8.
        cjk_part = "世" * 15_000   # 45 000 bytes
        ascii_part = "x" * 25_000      # 25 000 bytes  → total 70 000
        content = cjk_part + ascii_part
        self._assert_roundtrip(content, "mixed_70kb.txt")

    def test_empty_file(self):
        """Edge case: empty content."""
        self._assert_roundtrip("", "empty.txt")

    def test_exactly_at_chunk_boundary(self):
        """Content whose byte length is exactly CHUNK_SIZE."""
        content = "B" * CHUNK_SIZE
        self._assert_roundtrip(content, "exact_chunk.txt")


if __name__ == "__main__":
    unittest.main()
