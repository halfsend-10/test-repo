"""Buffered file writer with UTF-8-safe chunking.

Writes files in 64KB chunks while ensuring multibyte UTF-8 sequences
are never split across chunk boundaries.
"""

CHUNK_SIZE = 65536  # 64KB


def _utf8_safe_boundary(data: bytes, boundary: int) -> int:
    """Find the largest position <= boundary that does not split a
    multibyte UTF-8 sequence.

    UTF-8 continuation bytes have the form 10xxxxxx (0x80..0xBF).
    Walking backward from *boundary* until we hit a non-continuation
    byte gives us the start of the character that straddles the
    boundary.  We then check whether the full character fits before
    *boundary*; if not we cut just before it.

    Returns the safe split position (always <= boundary).
    """
    if boundary >= len(data):
        return len(data)

    pos = boundary
    # Walk back over continuation bytes (10xxxxxx).
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        pos -= 1

    # pos is now pointing at the leading byte of a character.
    # Determine expected character length from the leading byte.
    lead = data[pos]
    if lead < 0x80:
        char_len = 1
    elif lead < 0xE0:
        char_len = 2
    elif lead < 0xF0:
        char_len = 3
    else:
        char_len = 4

    # If the full character fits within the boundary, keep it.
    if pos + char_len <= boundary:
        return boundary

    # Otherwise, split just before this character.
    return pos


def save_file(content: str, path: str) -> None:
    """Write *content* to *path* using chunked I/O that respects
    UTF-8 character boundaries.

    The data is encoded to UTF-8 once, then written in chunks of up
    to ``CHUNK_SIZE`` bytes.  Chunk boundaries are adjusted so that
    multibyte characters are never split across writes.
    """
    data = content.encode("utf-8")

    with open(path, "wb") as fh:
        offset = 0
        while offset < len(data):
            end = min(offset + CHUNK_SIZE, len(data))
            if end < len(data):
                end = _utf8_safe_boundary(data, end)
            fh.write(data[offset:end])
            offset = end
