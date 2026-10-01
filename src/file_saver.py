"""Chunked file saver with UTF-8 multibyte boundary handling.

Writes file content in chunks to manage memory for large files.
Ensures UTF-8 multibyte sequences are never split across chunk
boundaries, which would cause encoding errors or crashes.
"""

import os

# Default chunk size: 64KB
DEFAULT_CHUNK_SIZE = 65536


def _find_safe_split(data: bytes, max_size: int) -> int:
    """Find a byte offset <= max_size that does not split a UTF-8 sequence.

    UTF-8 continuation bytes have the form 10xxxxxx (0x80–0xBF).
    If the byte at max_size is a continuation byte, walk backwards to
    the start of the multibyte sequence so the entire character stays
    in the current chunk.

    Args:
        data: The full byte buffer to split.
        max_size: The maximum number of bytes for this chunk.

    Returns:
        A safe split point that keeps UTF-8 sequences intact.
    """
    if max_size >= len(data):
        return len(data)

    pos = max_size
    # Walk backwards while we are on a continuation byte (10xxxxxx).
    # A well-formed UTF-8 sequence has at most 3 continuation bytes,
    # so we backtrack at most 3 positions.
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        pos -= 1

    # pos now points at the leading byte of a multibyte sequence (or a
    # single-byte ASCII character). The safe split is *at* pos so the
    # leading byte starts the next chunk together with its continuations.
    return pos


def save_file(content: str, path: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> int:
    """Save string content to a file using chunked writes.

    Encodes *content* as UTF-8 and writes it in chunks of at most
    *chunk_size* bytes, ensuring no chunk split falls inside a
    multibyte character.

    Args:
        content: The text to save.
        path: Destination file path.
        chunk_size: Maximum bytes per write (default 64 KB).

    Returns:
        Total number of bytes written.

    Raises:
        OSError: If the file cannot be opened or written.
    """
    data = content.encode("utf-8")
    total = len(data)
    written = 0

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(path, "wb") as fh:
        while written < total:
            end = min(written + chunk_size, total)
            safe_end = _find_safe_split(data, end)

            # Guard: if _find_safe_split returned 'written' (no progress),
            # the chunk_size is smaller than a single character — bump to
            # include the full sequence.
            if safe_end <= written:
                safe_end = end
                while safe_end < total and (data[safe_end] & 0xC0) == 0x80:
                    safe_end += 1

            fh.write(data[written:safe_end])
            written = safe_end

    return total
