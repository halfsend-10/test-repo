"""File saving module with proper UTF-8 multibyte character support.

This module handles saving files of arbitrary size, correctly
accounting for multibyte UTF-8 characters when allocating buffers.
"""

BUFFER_SIZE = 65536  # 64KB


def save_file(filepath: str, content: str) -> None:
    """Save content to a file, handling UTF-8 multibyte characters.

    The buffer size check uses byte length (not character count) to
    avoid overflows when the content contains multibyte characters
    such as emoji or CJK characters.

    Args:
        filepath: Path to the file to save.
        content: Text content to save.
    """
    encoded = content.encode("utf-8")
    _write_buffered(filepath, encoded)


def _write_buffered(filepath: str, data: bytes) -> None:
    """Write data to a file using buffered I/O.

    Splits the data into BUFFER_SIZE chunks and writes each chunk
    sequentially. Uses byte length for all size calculations so
    multibyte UTF-8 sequences are never truncated mid-character.

    Args:
        filepath: Path to the file to write.
        data: Raw bytes to write.
    """
    with open(filepath, "wb") as f:
        offset = 0
        while offset < len(data):
            chunk = data[offset : offset + BUFFER_SIZE]
            f.write(chunk)
            offset += len(chunk)
