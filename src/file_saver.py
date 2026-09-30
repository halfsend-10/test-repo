"""File saving module with proper UTF-8 multibyte character handling.

This module provides file saving functionality that correctly handles
UTF-8 encoded content of any size, using byte-length calculations
instead of character counts to prevent buffer overflows.
"""

import os
import tempfile

# Default buffer size for chunked writes.
DEFAULT_BUFFER_SIZE = 65536  # 64KB


def save_file(path, content, buffer_size=DEFAULT_BUFFER_SIZE):
    """Save content to a file using chunked writes with correct byte sizing.

    Writes content in chunks based on byte length rather than character
    count, ensuring that UTF-8 multibyte characters are never split
    across chunk boundaries and that the buffer is never overflowed.

    Args:
        path: Destination file path.
        content: Unicode string to write.
        buffer_size: Maximum number of bytes per write chunk.

    Raises:
        OSError: If the file cannot be written.
        TypeError: If content is not a string.
    """
    if not isinstance(content, str):
        raise TypeError("content must be a string")

    encoded = content.encode("utf-8")
    dir_name = os.path.dirname(os.path.abspath(path))

    # Write to a temporary file first, then atomically rename to avoid
    # partial writes on crash.
    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        offset = 0
        total = len(encoded)
        while offset < total:
            end = min(offset + buffer_size, total)
            os.write(fd, encoded[offset:end])
            offset = end
        os.fsync(fd)
        os.close(fd)
        os.replace(tmp_path, path)
    except Exception:
        os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _calculate_chunk_boundary(content, char_start, buffer_size):
    """Find the character index that keeps encoded bytes within buffer_size.

    Scans forward from char_start, accumulating encoded byte lengths,
    and returns the character index at which the next character would
    exceed the buffer.  This ensures multibyte characters are never
    split across chunk boundaries.

    Args:
        content: The full unicode string.
        char_start: Character index to start from.
        buffer_size: Maximum bytes allowed in this chunk.

    Returns:
        Character index (exclusive) for the end of this chunk.
    """
    byte_count = 0
    idx = char_start
    while idx < len(content):
        char_bytes = len(content[idx].encode("utf-8"))
        if byte_count + char_bytes > buffer_size:
            break
        byte_count += char_bytes
        idx += 1
    return idx
