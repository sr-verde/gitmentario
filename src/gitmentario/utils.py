import string
import unicodedata
from datetime import datetime
from pathlib import PurePosixPath

FALLBACK_NAME = "commenter"


def safe_name(
    name: str, whitespace_replacement: str = "_", fallback: str | None = None
) -> str:
    """Convert a string into a safe filename-friendly format.

    This function normalizes a given string by removing or replacing
    problematic characters to ensure it is safe to use as a filename.
    Unicode characters are normalized to ASCII, spaces are replaced with
    underscores, and only a restricted set of characters is allowed.

    Args:
        name (str): The input string to sanitize.
        whitespace_replacement (str): Whitespaces will be replaced with this string.
        fallback (str | None): Returned when nothing survives cleaning. When
            ``None``, an empty result raises instead.

    Returns:
        str: A cleaned string suitable for use as a filename.

    Raises:
        ValueError: If the resulting string is empty after cleaning and no
            ``fallback`` was given.
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
        if fallback is None:
            raise ValueError("Invalid name")
        return fallback

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


def rfc3339(moment: datetime) -> str:
    """Format an aware datetime the way SSG front matter expects it.

    An SSG parses `2026-09-04T15:13:38+00:00` and the same time ending in `Z`,
    but not both suffixes at once, and rejects the whole page when the date will
    not parse. `datetime.now(UTC)` is aware, so its `isoformat()` already ends in
    `+00:00` and must not have a `Z` appended as well.

    Args:
        moment (datetime): A timezone-aware UTC timestamp.

    Returns:
        str: An RFC 3339 timestamp ending in `Z`.
    """
    return moment.isoformat().replace("+00:00", "Z")
