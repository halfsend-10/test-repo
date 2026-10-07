"""File saving module with correct UTF-8 buffer handling.

Allocates write buffers based on byte length rather than character count
to prevent overflow when multibyte characters push the byte count past
the buffer boundary.
"""

import os

# 64KB buffer boundary
BUFFER_SIZE = 65536


def save_file(content: str, path: str) -> None:
    """Save content to a file, handling large files with multibyte characters.

    Uses byte-length-based buffer allocation to avoid overflow when
    content contains UTF-8 multibyte characters (emoji, CJK, etc.).

    Args:
        content: The text content to save.
        path: The file path to write to.
    """
    encoded = content.encode("utf-8")
    byte_length = len(encoded)

    with open(path, "wb") as f:
        offset = 0
        while offset < byte_length:
            end = min(offset + BUFFER_SIZE, byte_length)
            # Avoid splitting a multibyte character at the chunk boundary
            if end < byte_length:
                end = _find_safe_boundary(encoded, end)
            f.write(encoded[offset:end])
            offset = end


def _find_safe_boundary(data: bytes, pos: int) -> int:
    """Find the nearest safe UTF-8 boundary at or before pos.

    UTF-8 continuation bytes start with 0b10xxxxxx (0x80-0xBF).
    Walk backward from pos until we find a byte that is not a
    continuation byte, which is the start of a character.

    Args:
        data: The encoded byte string.
        pos: The candidate split position.

    Returns:
        A position at or before pos that does not split a character.
    """
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        pos -= 1
    return pos
