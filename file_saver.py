"""File saving module with correct UTF-8 buffer handling.

Allocates write buffers based on byte length rather than character count
to prevent buffer overflows when saving files containing multibyte
UTF-8 characters (emoji, CJK, etc.) that exceed 64KB.
"""

BUFFER_SIZE = 65536  # 64KB


def save_file(content: str, path: str) -> None:
    """Save content to a file, handling large UTF-8 content correctly.

    Uses byte length for buffer allocation to avoid under-sizing the
    buffer when content contains multibyte UTF-8 characters.

    Args:
        content: The text content to save.
        path: The file path to write to.
    """
    encoded = content.encode("utf-8")
    byte_length = len(encoded)

    with open(path, "wb") as f:
        offset = 0
        while offset < byte_length:
            end = min(offset + BUFFER_SIZE, byte_length)
            f.write(encoded[offset:end])
            offset = end


def calculate_buffer_size(content: str) -> int:
    """Calculate the required buffer size for the given content.

    Returns the byte length of the UTF-8 encoded content, not the
    character count. This is the fix for the v2.3.1 regression where
    character count was used instead, causing under-allocation for
    multibyte content.

    Args:
        content: The text content to measure.

    Returns:
        The byte length of the content when encoded as UTF-8.
    """
    return len(content.encode("utf-8"))
