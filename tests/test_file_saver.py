"""Tests for the file_saver module.

Covers the UTF-8 multibyte buffer-sizing fix (issue #1512).
"""

from src.file_saver import BUFFER_SIZE, _count_chars_for_byte_budget, save_file


class TestCountCharsForByteBudget:
    """Tests for _count_chars_for_byte_budget."""

    def test_ascii_only(self):
        """ASCII characters each consume one byte."""
        data = "a" * 100
        result = _count_chars_for_byte_budget(data, 0, 50)
        assert result == 50

    def test_two_byte_chars(self):
        """Accented Latin characters each consume two UTF-8 bytes."""
        data = "é" * 20  # 20 e-acute characters
        result = _count_chars_for_byte_budget(data, 0, 10)
        # 10 bytes fits exactly 5 two-byte chars
        assert result == 5

    def test_emoji_four_byte_chars(self):
        """Emoji characters each consume four UTF-8 bytes."""
        # Each emoji is 4 bytes in UTF-8
        data = "\U0001f600" * 20  # 20 grinning face emoji
        result = _count_chars_for_byte_budget(data, 0, 16)
        # 16 bytes fits exactly 4 emoji (4 bytes each)
        assert result == 4

    def test_cjk_three_byte_chars(self):
        """CJK characters each consume three UTF-8 bytes."""
        # CJK characters are 3 bytes in UTF-8
        data = "世" * 20  # 20 copies of CJK char
        result = _count_chars_for_byte_budget(data, 0, 15)
        # 15 bytes fits exactly 5 CJK chars (3 bytes each)
        assert result == 5

    def test_partial_fit(self):
        """A multibyte character that would exceed the budget is excluded."""
        # 4-byte emoji should not partially fit
        data = "\U0001f600" * 5
        result = _count_chars_for_byte_budget(data, 0, 7)
        # Only 1 emoji fits (4 bytes), next would need 8
        assert result == 1

    def test_offset(self):
        """Counting starts from the given offset into the string."""
        data = "abcde"
        result = _count_chars_for_byte_budget(data, 2, 2)
        assert result == 2  # 'c' and 'd'

    def test_empty_string(self):
        """An empty string yields zero characters."""
        result = _count_chars_for_byte_budget("", 0, 100)
        assert result == 0

    def test_zero_max_bytes(self):
        """A zero-byte budget yields zero characters."""
        result = _count_chars_for_byte_budget("abc", 0, 0)
        assert result == 0


class TestSaveFile:
    """Tests for the save_file function."""

    def test_save_large_file_with_emoji(self, tmp_path):
        """Save a 65KB+ document containing emoji (4-byte UTF-8)."""
        emoji_char = "\U0001f600"  # 4 bytes each
        # 17000 emoji = 68000 bytes > 64KB
        content = emoji_char * 17000
        path = tmp_path / "out.txt"

        save_file(str(path), content)
        result = path.read_text(encoding="utf-8")

        assert result == content
        assert path.stat().st_size == len(content.encode("utf-8"))

    def test_save_large_file_with_cjk(self, tmp_path):
        """Save a 64KB document with CJK characters (3-byte UTF-8)."""
        cjk_char = "世"  # 3 bytes each
        # 22000 chars * 3 bytes = 66000 bytes > 64KB
        content = cjk_char * 22000
        path = tmp_path / "out.txt"

        save_file(str(path), content)
        result = path.read_text(encoding="utf-8")

        assert result == content

    def test_save_large_ascii_file(self, tmp_path):
        """Verify ASCII-only files >64KB still save correctly."""
        content = "A" * 70000  # 70KB of ASCII
        path = tmp_path / "out.txt"

        save_file(str(path), content)
        result = path.read_text(encoding="utf-8")

        assert result == content
        assert path.stat().st_size == 70000

    def test_save_boundary_char_count_fits_byte_count_exceeds(self, tmp_path):
        """File whose character count fits in 64KB but byte count exceeds it.

        This is the core regression case: if the buffer used character
        count, 20000 emoji (20000 chars < 65536) would appear to fit,
        but their byte representation (80000 bytes) would overflow a
        64KB buffer.
        """
        emoji_char = "\U0001f600"  # 4 bytes each
        # 20000 chars < 65536 char limit, but 80000 bytes > 65536 byte limit
        content = emoji_char * 20000
        path = tmp_path / "out.txt"

        save_file(str(path), content)
        result = path.read_text(encoding="utf-8")

        assert result == content
        assert path.stat().st_size == 80000

    def test_save_small_file(self, tmp_path):
        """Files under 64KB should still save correctly."""
        content = "Hello, world! \U0001f30d"
        path = tmp_path / "out.txt"

        save_file(str(path), content)
        result = path.read_text(encoding="utf-8")

        assert result == content

    def test_save_empty_file(self, tmp_path):
        """Empty content should produce an empty file."""
        path = tmp_path / "out.txt"

        save_file(str(path), "")
        result = path.read_text(encoding="utf-8")

        assert result == ""

    def test_save_mixed_encoding(self, tmp_path):
        """Mixed ASCII and multibyte characters spanning the buffer boundary."""
        ascii_part = "x" * (BUFFER_SIZE - 10)
        emoji_part = "\U0001f600" * 100  # 400 bytes of emoji
        content = ascii_part + emoji_part
        path = tmp_path / "out.txt"

        save_file(str(path), content)
        result = path.read_text(encoding="utf-8")

        assert result == content
