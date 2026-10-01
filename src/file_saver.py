"""File saving module with proper UTF-8 buffer handling.

Provides buffered file writing that correctly handles multibyte UTF-8
characters by calculating buffer sizes in bytes rather than characters.
"""

import os
import tempfile

# Buffer size in bytes for chunked file writing.
BUFFER_SIZE = 65536  # 64KB


def _calculate_byte_length(content: str) -> int:
    """Return the byte length of a string when encoded as UTF-8."""
    return len(content.encode("utf-8"))


def save_file(path: str, content: str) -> None:
    """Save content to a file using byte-aware buffered writing.

    Writes content in chunks based on byte size (not character count)
    to correctly handle UTF-8 multibyte characters that may expand
    beyond the buffer boundary.

    Args:
        path: Destination file path.
        content: Text content to write.

    Raises:
        OSError: If the file cannot be written.
    """
    encoded = content.encode("utf-8")
    dir_name = os.path.dirname(path) or "."

    # Write to a temp file first, then rename for atomicity.
    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        offset = 0
        while offset < len(encoded):
            chunk = encoded[offset : offset + BUFFER_SIZE]
            os.write(fd, chunk)
            offset += len(chunk)
        os.close(fd)
        fd = -1
        os.replace(tmp_path, path)
    except BaseException:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_file(path: str) -> str:
    """Load and return the text content of a file.

    Args:
        path: Source file path.

    Returns:
        The decoded text content.

    Raises:
        OSError: If the file cannot be read.
    """
    with open(path, "rb") as f:
        return f.read().decode("utf-8")
