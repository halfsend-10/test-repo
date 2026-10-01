"""File saving module with proper UTF-8 buffer handling.

This module provides file saving functionality that correctly allocates
buffers based on byte length rather than character count, preventing
buffer overflows when saving files containing multibyte UTF-8 characters
(e.g., emoji, CJK characters) that exceed 64KB.
"""

# Default buffer size in bytes (64KB).
BUFFER_SIZE = 65536


def save_file(content: str, path: str) -> None:
    """Save content to a file, handling UTF-8 multibyte characters correctly.

    The content is encoded to UTF-8 bytes and written in chunks sized by
    byte length (not character count) to avoid buffer overflows when
    multibyte characters cause the byte representation to exceed the
    buffer size.

    Args:
        content: The text content to save.
        path: The file path to write to.
    """
    encoded = content.encode("utf-8")
    with open(path, "wb") as f:
        offset = 0
        while offset < len(encoded):
            chunk = encoded[offset : offset + BUFFER_SIZE]
            f.write(chunk)
            offset += len(chunk)
