"""File handler module for saving documents.

Handles file I/O with proper UTF-8 encoding support, including correct
buffer allocation based on byte length rather than character count.
"""

# Maximum buffer size for chunked writes (64KB)
BUFFER_SIZE = 65536


def save_file(content: str, filepath: str) -> int:
    """Save content to a file with proper UTF-8 encoding.

    Writes content in chunks, allocating buffers based on the byte
    length of the encoded content rather than character count. This
    ensures multibyte UTF-8 characters (emoji, CJK, etc.) are handled
    correctly for files of any size.

    The caller is responsible for validating and sanitizing
    ``filepath`` before calling this function. No path
    canonicalization, directory restriction, or symlink checks are
    performed.

    Args:
        content: The string content to save.
        filepath: The destination file path.

    Returns:
        The number of bytes written.

    Raises:
        OSError: If the file cannot be written.
        ValueError: If content is None.
    """
    if content is None:
        raise ValueError("content must not be None")

    encoded = content.encode("utf-8")
    total_bytes = len(encoded)

    with open(filepath, "wb") as f:
        offset = 0
        while offset < total_bytes:
            chunk = encoded[offset : offset + BUFFER_SIZE]
            written = f.write(chunk)
            offset += written

    return total_bytes
