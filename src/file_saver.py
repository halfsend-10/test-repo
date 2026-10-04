"""File saver module with chunked write support.

Handles writing large files in chunks while preserving UTF-8 character
boundaries. Prior to the fix, a fixed 64KB chunk size could split
multibyte UTF-8 sequences, causing data corruption or crashes.
"""

import os

# Default chunk size for writing files (64KB).
CHUNK_SIZE = 65536


def _find_safe_split(data: bytes, max_size: int) -> int:
    """Find the largest split point <= max_size that does not break a UTF-8 sequence.

    UTF-8 continuation bytes have the bit pattern 10xxxxxx (0x80-0xBF).
    If the byte at the proposed split point is a continuation byte, back
    up until we find a leading byte (or the start of the buffer), then
    split just before that leading byte so the entire character stays in
    the next chunk.

    Args:
        data: The bytes buffer to split.
        max_size: The maximum number of bytes in the first chunk.

    Returns:
        The safe split index (<= max_size).
    """
    if max_size >= len(data):
        return len(data)

    pos = max_size
    # Walk backwards past any continuation bytes (10xxxxxx).
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        pos -= 1

    # If we backed up all the way, something is very wrong with the
    # encoding — fall back to the original position to avoid an
    # infinite loop.
    if pos == 0:
        return max_size

    return pos


def save_file(path: str, content: str, chunk_size: int = CHUNK_SIZE) -> None:
    """Save *content* to *path*, writing in chunks that respect UTF-8 boundaries.

    Args:
        path: Destination file path.
        content: The text content to write.
        chunk_size: Maximum bytes per write call (default 64KB).
    """
    data = content.encode("utf-8")
    tmp_path = path + ".tmp"

    try:
        with open(tmp_path, "wb") as fh:
            offset = 0
            while offset < len(data):
                remaining = len(data) - offset
                end = offset + min(remaining, chunk_size)
                # Ensure we don't split a multibyte character.
                end = offset + _find_safe_split(data[offset:], min(remaining, chunk_size))
                fh.write(data[offset:end])
                offset = end

        # Atomic rename so readers never see a partial file.
        os.replace(tmp_path, path)
    except BaseException:
        # Clean up the temp file on any failure.
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_file(path: str) -> str:
    """Load and return the text content of *path*.

    Args:
        path: File path to read.

    Returns:
        The decoded text content.
    """
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()
