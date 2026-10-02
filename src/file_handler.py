"""File handler module for saving documents.

Handles file I/O with proper UTF-8 encoding support, including correct
buffer allocation based on byte length rather than character count.
"""

import os
import tempfile

# Maximum buffer size for chunked writes (64KB)
BUFFER_SIZE = 65536


def save_file(content: str, filepath: str) -> int:
    """Save content to a file with proper UTF-8 encoding.

    Writes content in chunks, allocating buffers based on the byte
    length of the encoded content rather than character count. This
    ensures multibyte UTF-8 characters (emoji, CJK, etc.) are handled
    correctly for files of any size.

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

    # Write to a temporary file first, then atomically rename to avoid
    # partial writes on failure.
    dir_name = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(dir_name, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        offset = 0
        while offset < total_bytes:
            chunk = encoded[offset : offset + BUFFER_SIZE]
            os.write(fd, chunk)
            offset += len(chunk)
        os.close(fd)
        os.replace(tmp_path, filepath)
    except Exception:
        os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return total_bytes


def load_file(filepath: str) -> str:
    """Load a UTF-8 encoded file and return its content as a string.

    Args:
        filepath: The file path to read.

    Returns:
        The file content as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        UnicodeDecodeError: If the file is not valid UTF-8.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
