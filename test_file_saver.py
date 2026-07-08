"""Tests for file_saver module.

Covers the UTF-8 multibyte character save bug described in issue #68:
segfault when saving files larger than 64KB containing multibyte chars.
"""

import os
import tempfile

from file_saver import BUFFER_SIZE, save_file


def test_save_under_64kb_with_multibyte():
    """File just under 64KB with multibyte chars saves successfully."""
    # Each emoji is 4 bytes in UTF-8; fill to just under 64KB
    char = "\U0001f600"  # grinning face emoji, 4 bytes
    byte_target = BUFFER_SIZE - 4
    count = byte_target // len(char.encode("utf-8"))
    content = char * count
    assert len(content.encode("utf-8")) < BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        path = f.name
    try:
        save_file(path, content)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_over_64kb_ascii_only():
    """File just over 64KB with ASCII only saves successfully."""
    content = "A" * (BUFFER_SIZE + 1024)
    assert len(content.encode("utf-8")) > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        path = f.name
    try:
        save_file(path, content)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_over_64kb_with_multibyte():
    """File just over 64KB with multibyte chars saves successfully.

    This is the case that previously caused a segfault due to buffer
    allocation using character count instead of byte length.
    """
    # Use 4-byte emoji to ensure byte length exceeds 64KB
    char = "\U0001f600"
    byte_target = BUFFER_SIZE + 4096
    count = byte_target // len(char.encode("utf-8"))
    content = char * count
    assert len(content.encode("utf-8")) > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        path = f.name
    try:
        save_file(path, content)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_large_file_mixed_content():
    """Large file (1MB+) with mixed ASCII and multibyte content."""
    # Mix ASCII and emoji to create >1MB of content
    segment = "Hello world! \U0001f30d\U0001f680 " * 100
    byte_target = 1024 * 1024 + 1024  # just over 1MB
    repeats = byte_target // len(segment.encode("utf-8")) + 1
    content = segment * repeats
    assert len(content.encode("utf-8")) > 1024 * 1024

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        path = f.name
    try:
        save_file(path, content)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_empty_file():
    """Empty content saves without error."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        path = f.name
    try:
        save_file(path, "")
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == b""
    finally:
        os.unlink(path)


def test_round_trip_cjk_characters():
    """CJK characters (3 bytes each in UTF-8) round-trip correctly."""
    # CJK chars are 3 bytes each; create content spanning buffer boundary
    char = "世"  # 世, 3 bytes in UTF-8
    count = (BUFFER_SIZE + 2048) // 3
    content = char * count
    assert len(content.encode("utf-8")) > BUFFER_SIZE

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        path = f.name
    try:
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            loaded = f.read()
        assert loaded == content
    finally:
        os.unlink(path)
