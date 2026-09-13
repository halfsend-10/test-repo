"""File save handler with correct UTF-8 multibyte character support.

This module provides a chunked file save routine that respects UTF-8
multibyte character boundaries when splitting data into buffer-sized
chunks. It prevents the segmentation fault that occurred when a
multibyte sequence was split across the 64KB buffer boundary.
"""

import os

BUFFER_SIZE = 65536  # 64KB


def save_file(content: str, path: str) -> None:
    """Save content to a file using chunked writes.

    Encodes the content as UTF-8 and writes it in BUFFER_SIZE chunks,
    ensuring that multibyte character sequences are never split across
    chunk boundaries.

    Args:
        content: The text content to save.
        path: The file path to write to.

    Raises:
        OSError: If the file cannot be written.
    """
    data = content.encode("utf-8")
    offset = 0
    tmp_path = path + ".tmp"

    try:
        with open(tmp_path, "wb") as f:
            while offset < len(data):
                end = min(offset + BUFFER_SIZE, len(data))

                # If we're not at the very end, make sure we don't
                # split a multibyte UTF-8 sequence at the chunk
                # boundary.
                if end < len(data):
                    end = _adjust_for_utf8_boundary(data, end)

                f.write(data[offset:end])
                offset = end

        os.replace(tmp_path, path)
    except BaseException:
        # Clean up the temporary file on any failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _adjust_for_utf8_boundary(data: bytes, pos: int) -> int:
    """Move pos backward so it does not land inside a multibyte sequence.

    UTF-8 continuation bytes have the bit pattern 10xxxxxx (0x80..0xBF).
    If the byte at *pos* is a continuation byte, we walk backward until
    we find the leading byte of that character, and return that index so
    the entire character stays in the current chunk.

    Args:
        data: The full UTF-8 encoded byte string.
        pos: The proposed split position.

    Returns:
        An adjusted position that does not split a multibyte character.
    """
    # Walk back at most 3 bytes (the maximum number of continuation
    # bytes in a valid UTF-8 sequence is 3, for a 4-byte character).
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        pos -= 1
    return pos
