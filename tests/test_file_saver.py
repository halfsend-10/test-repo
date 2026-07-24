"""Tests for file_saver module.

Covers the fix for issue #648: segfault when saving files >64KB
containing UTF-8 multibyte characters.
"""

import os
import tempfile

from src.file_saver import CHUNK_SIZE, save_file


def test_save_ascii_file_over_64kb():
    """ASCII-only content over 64KB saves without error."""
    content = "A" * (CHUNK_SIZE + 1024)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            result = f.read()
        assert result == content
    finally:
        os.unlink(path)


def test_save_multibyte_utf8_over_64kb():
    """Multibyte UTF-8 content (emoji) over 64KB saves without error."""
    # Each emoji is 4 bytes in UTF-8; fill past 64KB
    emoji_count = (CHUNK_SIZE // 4) + 256
    content = "\U0001f600" * emoji_count  # grinning face emoji
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            result = f.read()
        assert result == content
    finally:
        os.unlink(path)


def test_save_multibyte_spanning_chunk_boundary():
    """Multibyte character at the exact 64KB chunk boundary is handled."""
    # Build content where a multibyte char lands on the boundary
    padding = "x" * (CHUNK_SIZE - 1)  # 1 byte short of boundary
    # Next char is a 3-byte UTF-8 character that would span the boundary
    content = padding + "世" + "y" * 1024  # CJK character
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            result = f.read()
        assert result == content
    finally:
        os.unlink(path)


def test_save_only_multibyte_over_64kb():
    """File consisting entirely of multibyte characters over 64KB."""
    # CJK characters are 3 bytes each in UTF-8
    char_count = (CHUNK_SIZE // 3) + 512
    content = "世" * char_count  # CJK 'world' character
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            result = f.read()
        assert result == content
    finally:
        os.unlink(path)


def test_save_small_file():
    """Files under 64KB still save correctly."""
    content = "Hello, world! \U0001f30d"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            result = f.read()
        assert result == content
    finally:
        os.unlink(path)
