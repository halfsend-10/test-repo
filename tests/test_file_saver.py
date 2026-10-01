"""Tests for file_saver module.

Verifies that files containing UTF-8 multibyte characters save correctly
at and above the 64KB buffer boundary.
"""

import os
import tempfile

from src.file_saver import BUFFER_SIZE, save_file


def test_save_ascii_under_buffer_size():
    """ASCII content under 64KB saves correctly."""
    content = "a" * (BUFFER_SIZE - 1)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_ascii_over_buffer_size():
    """ASCII content over 64KB saves correctly."""
    content = "a" * (BUFFER_SIZE + 1000)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
    finally:
        os.unlink(path)


def test_save_emoji_under_buffer_size():
    """Emoji content under 64KB (by byte count) saves correctly."""
    # Each emoji is 4 bytes in UTF-8; use enough to stay under 64KB
    emoji_count = (BUFFER_SIZE // 4) - 10
    content = "\U0001f600" * emoji_count
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
        assert saved.decode("utf-8") == content
    finally:
        os.unlink(path)


def test_save_emoji_over_buffer_size():
    """Emoji content over 64KB (by byte count) saves correctly.

    This is the primary regression test for the bug: when the buffer was
    sized by character count, emoji (4 bytes each in UTF-8) caused a
    buffer overflow past 64KB.
    """
    # Each emoji is 4 bytes in UTF-8; 20000 emoji = 80KB > 64KB
    emoji_count = 20000
    content = "\U0001f600" * emoji_count
    byte_len = len(content.encode("utf-8"))
    assert byte_len > BUFFER_SIZE, (
        f"Test content must exceed buffer size: {byte_len} <= {BUFFER_SIZE}"
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
        assert saved.decode("utf-8") == content
        assert len(saved) == byte_len
    finally:
        os.unlink(path)


def test_save_cjk_over_buffer_size():
    """CJK content over 64KB (by byte count) saves correctly.

    CJK characters are 3 bytes each in UTF-8.
    """
    # 25000 CJK chars = 75KB > 64KB
    cjk_count = 25000
    content = "世" * cjk_count  # '世' repeated
    byte_len = len(content.encode("utf-8"))
    assert byte_len > BUFFER_SIZE
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
        assert saved.decode("utf-8") == content
    finally:
        os.unlink(path)


def test_save_mixed_content_over_buffer_size():
    """Mixed ASCII + emoji + CJK content over 64KB saves correctly."""
    ascii_part = "Hello World! " * 1000  # ~13KB
    emoji_part = "\U0001f680\U0001f30d" * 5000  # ~40KB
    cjk_part = "世界" * 5000  # ~30KB
    content = ascii_part + emoji_part + cjk_part
    byte_len = len(content.encode("utf-8"))
    assert byte_len > BUFFER_SIZE
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        path = tmp.name
    try:
        save_file(content, path)
        with open(path, "rb") as f:
            saved = f.read()
        assert saved == content.encode("utf-8")
        assert saved.decode("utf-8") == content
    finally:
        os.unlink(path)
