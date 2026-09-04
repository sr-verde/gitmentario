from datetime import UTC, datetime, timedelta, timezone
from pathlib import PurePosixPath

from pytest import mark, raises

from gitmentario.utils import (
    FALLBACK_NAME,
    check_repo_relative,
    rfc3339,
    safe_name,
)


@mark.parametrize(
    ("raw", "expected"),
    [
        ("valid_name-123", "valid_name-123"),
        # Unicode is normalized to ASCII: é becomes e, ä becomes a
        ("café_ä", "cafe_a"),
        ("日本語 Bob", "Bob"),
        # Only the delimiters are dropped, so a tag body survives as text
        ('inva<lid>:na"me/\\|?*', "invalidname"),
        ("invalid<strong>name</strong>", "invalidstrongnamestrong"),
        ("this is a test", "this_is_a_test"),
        ("filename.   ", "filename"),
        ("  .filename", "filename"),
        (
            "-_.()ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
            "-_.()ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        ),
    ],
)
def test_safe_name_cleans_input(raw: str, expected: str) -> None:
    assert safe_name(raw) == expected


@mark.parametrize(
    ("replacement", "expected"),
    [("_", "this_is_a_test"), ("-", "this-is-a-test"), ("", "thisisatest")],
)
def test_safe_name_replaces_whitespace(replacement: str, expected: str) -> None:
    assert safe_name("this is a test", replacement) == expected


@mark.parametrize("raw", ["<<::>>", "...", "日本語", "Дмитрий", "  ' "])
def test_safe_name_raises_when_nothing_survives(raw: str) -> None:
    """Without a fallback the caller decides what an unusable name means."""
    with raises(ValueError):
        safe_name(raw)


@mark.parametrize("raw", ["<<::>>", "...", "日本語", "Дмитрий", "  ' "])
def test_safe_name_returns_fallback_when_nothing_survives(raw: str) -> None:
    """A name in a non-Latin script normalizes away, and must not fail a request."""
    assert safe_name(raw, fallback=FALLBACK_NAME) == FALLBACK_NAME


@mark.parametrize("raw", ["Bob", "日本語 Bob", "b"])
def test_safe_name_ignores_fallback_when_input_survives(raw: str) -> None:
    assert safe_name(raw, fallback=FALLBACK_NAME) != FALLBACK_NAME


@mark.parametrize("path", ["content", "a/b/c", "content/comments", "a.b/c-d", "."])
def test_check_repo_relative_accepts_relative_paths(path: str) -> None:
    candidate = PurePosixPath(path)
    assert check_repo_relative(candidate) is candidate


@mark.parametrize(
    "path",
    [
        "/absolute",
        "/",
        "/etc/passwd",
        "..",
        "../escape",
        "content/../../escape",
        "content/..",
    ],
)
def test_check_repo_relative_rejects_paths_leaving_the_repository(path: str) -> None:
    with raises(ValueError):
        check_repo_relative(PurePosixPath(path))


def test_rfc3339_ends_in_z_without_a_double_suffix() -> None:
    """`isoformat()` on an aware datetime already carries `+00:00`.

    Appending a literal `Z` to that yields `+00:00Z`, which still ends in `Z`
    but parses nowhere and makes an SSG reject the page.
    """
    formatted = rfc3339(datetime(2026, 9, 4, 15, 13, 38, tzinfo=UTC))
    assert formatted == "2026-09-04T15:13:38Z"


def test_rfc3339_round_trips() -> None:
    moment = datetime.now(UTC)
    assert datetime.fromisoformat(rfc3339(moment)) == moment


def test_rfc3339_leaves_other_offsets_intact() -> None:
    """Only UTC collapses to `Z`; a different offset must stay explicit."""
    berlin = datetime(2026, 9, 4, 17, 13, 38, tzinfo=timezone(timedelta(hours=2)))
    assert rfc3339(berlin) == "2026-09-04T17:13:38+02:00"
