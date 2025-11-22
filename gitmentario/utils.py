import string
import unicodedata


def safe_name(name: str, whitespace_replacement: str = "_") -> str:
    """Convert a string into a safe filename-friendly format.

    This function normalizes a given string by removing or replacing
    problematic characters to ensure it is safe to use as a filename.
    Unicode characters are normalized to ASCII, spaces are replaced with
    underscores, and only a restricted set of characters is allowed.

    Args:
        name (str): The input string to sanitize.
        whitespace_replacement (str): Whitespaces will be replaced with this string.

    Returns:
        str: A cleaned string suitable for use as a filename.

    Raises:
        ValueError: If the resulting string is empty after cleaning.
    """
    # Normalize unicode characters to ASCII
    name = unicodedata.normalize("NFKD", name).encode("ASCII", "ignore").decode("ASCII")
    # Strip trailing dots and spaces
    name = name.strip(" .")
    # Replace spaces with underscore
    name = name.replace(" ", whitespace_replacement)
    # Allowed characters for safe filenames
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    # Filter to keep only allowed characters
    cleaned = "".join(c for c in name if c in valid_chars)

    if not cleaned:
        raise ValueError("Invalid name")

    return cleaned
