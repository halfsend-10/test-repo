"""Tests for file_saver — verifies correct handling of UTF-8 multibyte
characters in files around and above the 64KB buffer boundary.
"""

import os
import sys
import tempfile

# Allow imports from src/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "src"))

from file_saver import WRITE_BUFFER_SIZE, save_file


def _round_trip(content: str) -> str:
    """Save *content* via save_file, read it back, and return the result."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as tmp:
        tmp_path = tmp.name
    try:
        save_file(tmp_path, content)
        with open(tmp_path, "r", encoding="utf-8") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)


# ------------------------------------------------------------------ #
# 1. File just under 64KB with multibyte chars → saves OK
# ------------------------------------------------------------------ #
def test_under_64kb_with_multibyte_chars():
    # Each emoji is 4 bytes in UTF-8.  Fill to just under the boundary.
    emoji = "\U0001F600"  # 😀
    count = (WRITE_BUFFER_SIZE // len(emoji.encode("utf-8"))) - 1
    content = emoji * count
    assert len(content.encode("utf-8")) < WRITE_BUFFER_SIZE
    assert _round_trip(content) == content


# ------------------------------------------------------------------ #
# 2. File just over 64KB with ASCII only → saves OK
# ------------------------------------------------------------------ #
def test_over_64kb_ascii_only():
    content = "A" * (WRITE_BUFFER_SIZE + 1024)
    assert len(content.encode("utf-8")) > WRITE_BUFFER_SIZE
    assert _round_trip(content) == content


# ------------------------------------------------------------------ #
# 3. File just over 64KB with multibyte chars → saves OK
#    (This is the exact scenario that previously crashed.)
# ------------------------------------------------------------------ #
def test_over_64kb_with_multibyte_chars():
    emoji = "\U0001F600"
    count = (WRITE_BUFFER_SIZE // len(emoji.encode("utf-8"))) + 256
    content = emoji * count
    assert len(content.encode("utf-8")) > WRITE_BUFFER_SIZE
    assert _round_trip(content) == content


# ------------------------------------------------------------------ #
# 4. Multibyte character spanning the exact 64KB byte boundary
# ------------------------------------------------------------------ #
def test_multibyte_spanning_boundary():
    # Place a 4-byte emoji right at the boundary so it straddles it.
    padding_bytes = WRITE_BUFFER_SIZE - 2  # 2 bytes short of boundary
    padding = "x" * padding_bytes  # each 'x' is 1 byte in UTF-8
    emoji = "\U0001F600"  # 4 bytes — starts at 65534, ends at 65538
    content = padding + emoji + "tail"
    encoded = content.encode("utf-8")
    assert encoded[WRITE_BUFFER_SIZE - 2 : WRITE_BUFFER_SIZE + 2] == emoji.encode(
        "utf-8"
    )
    assert _round_trip(content) == content


# ------------------------------------------------------------------ #
# 5. Large file (1MB+) with mixed content
# ------------------------------------------------------------------ #
def test_large_mixed_content():
    block = "Hello 世界! 🌍🌎🌏 — mixed ASCII, CJK, emoji.\n"
    repetitions = (1024 * 1024) // len(block.encode("utf-8")) + 1
    content = block * repetitions
    assert len(content.encode("utf-8")) > 1024 * 1024
    assert _round_trip(content) == content


# ------------------------------------------------------------------ #
# 6. Returned byte count matches actual encoded size
# ------------------------------------------------------------------ #
def test_bytes_written_matches_encoded_length():
    content = "café ☕ naïve résumé 日本語"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as tmp:
        tmp_path = tmp.name
    try:
        written = save_file(tmp_path, content)
        assert written == len(content.encode("utf-8"))
    finally:
        os.unlink(tmp_path)
