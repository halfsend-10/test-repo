"""File saver with correct UTF-8 buffer handling.

Fix for issue #1411: The previous implementation allocated the write
buffer based on character count (len(text)), which is correct for ASCII
but underestimates the byte size when multibyte UTF-8 characters are
present.  For content above the 64 KiB chunk threshold this caused a
buffer overflow / segfault.

The fix uses len(text.encode("utf-8")) — the actual byte length — when
sizing the buffer and when chunking writes.
"""

# 64 KiB chunk size used for buffered writes.
CHUNK_SIZE = 64 * 1024


def save_file(path: str, content: str) -> int:
    """Write *content* to *path* using chunked, byte-aware buffering.

    Returns the number of bytes written.
    """
    encoded = content.encode("utf-8")
    total_bytes = len(encoded)

    bytes_written = 0
    with open(path, "wb") as fh:
        while bytes_written < total_bytes:
            end = min(bytes_written + CHUNK_SIZE, total_bytes)
            fh.write(encoded[bytes_written:end])
            bytes_written = end

    return bytes_written
