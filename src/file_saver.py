"""File saving module with correct UTF-8 buffer handling.

This module handles writing file content to disk in chunks,
using byte length (not character count) for buffer allocation
to avoid buffer overruns with multibyte UTF-8 characters.
"""

CHUNK_SIZE = 65536  # 64KB


def save_file(filepath, content):
    """Save content to a file, chunking by byte length.

    Uses byte-aware chunking to correctly handle UTF-8 multibyte
    characters (emoji, CJK, etc.) that span chunk boundaries.

    Args:
        filepath: Path to the output file.
        content: String content to write.

    Raises:
        OSError: If the file cannot be written.
    """
    encoded = content.encode("utf-8")
    with open(filepath, "wb") as f:
        offset = 0
        while offset < len(encoded):
            chunk = encoded[offset : offset + CHUNK_SIZE]
            f.write(chunk)
            offset += CHUNK_SIZE
