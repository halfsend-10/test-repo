"""File saving utility with proper UTF-8 multibyte character handling.

Fixes a buffer overflow that occurred when saving files larger than 64KB
containing UTF-8 multibyte characters (e.g., emoji or CJK characters).
The previous implementation allocated the write buffer based on character
count (len(text)) rather than byte length (len(text.encode('utf-8'))),
causing a segmentation fault when multibyte characters pushed the byte
count past the buffer boundary.
"""

# Buffer size in bytes for chunked file writes.
WRITE_BUFFER_SIZE = 65536  # 64KB


def save_file(path: str, content: str) -> int:
    """Save content to a file, correctly handling UTF-8 multibyte characters.

    Writes the file in chunks using a byte-based buffer. The buffer size
    is calculated from the encoded byte length of each chunk, not from
    the character count, to prevent overflow when multibyte characters
    are present.

    Args:
        path: Destination file path.
        content: Text content to save.

    Returns:
        The number of bytes written.
    """
    encoded = content.encode("utf-8")
    bytes_written = 0

    with open(path, "wb") as f:
        offset = 0
        while offset < len(encoded):
            chunk = encoded[offset : offset + WRITE_BUFFER_SIZE]
            f.write(chunk)
            bytes_written += len(chunk)
            offset += WRITE_BUFFER_SIZE

    return bytes_written
