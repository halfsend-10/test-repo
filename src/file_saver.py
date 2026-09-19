"""File saving module with buffered write support.

Handles saving files of arbitrary size with proper UTF-8 encoding
support. Uses byte-length-based buffer sizing to correctly handle
multibyte characters.
"""

BUFFER_SIZE = 65536  # 64KB buffer


def _calculate_buffer_byte_size(data: str, offset: int, max_bytes: int) -> int:
    """Return the number of characters from offset that fit within max_bytes.

    Counts the encoded byte length of each character so that multibyte
    UTF-8 characters (emoji, CJK, accented letters, etc.) are measured
    correctly. This prevents the encoded chunk from exceeding the
    buffer size.
    """
    byte_count = 0
    char_count = 0
    for char in data[offset:]:
        char_bytes = len(char.encode("utf-8"))
        if byte_count + char_bytes > max_bytes:
            break
        byte_count += char_bytes
        char_count += 1
    return char_count


def save_file(path: str, content: str) -> None:
    """Save content to a file using buffered writes.

    Splits the content into chunks that each fit within BUFFER_SIZE
    bytes when UTF-8 encoded. This avoids buffer overflows when the
    content contains multibyte characters.

    Args:
        path: Destination file path.
        content: Text content to save.
    """
    with open(path, "w", encoding="utf-8") as f:
        offset = 0
        while offset < len(content):
            chunk_chars = _calculate_buffer_byte_size(
                content, offset, BUFFER_SIZE
            )
            if chunk_chars == 0:
                # Single character exceeds buffer (should not happen
                # with 64KB buffer, but guard against it).
                chunk_chars = 1
            f.write(content[offset : offset + chunk_chars])
            offset += chunk_chars
