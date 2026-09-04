import string
import unicodedata
from pathlib import PurePosixPath


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


def check_repo_relative(path: PurePosixPath) -> PurePosixPath:
    """Reject absolute paths and paths escaping the repository root.

    Forge APIs address files by repo-relative path, so a path that is absolute
    or contains ``..`` segments would resolve outside the directory it is meant
    to be confined to.

    Args:
        path (PurePosixPath): The path to check.

    Returns:
        PurePosixPath: The unchanged path.

    Raises:
        ValueError: If the path is absolute or contains a ``..`` segment.
    """
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Must be a relative path without '..' segments")
    return path
