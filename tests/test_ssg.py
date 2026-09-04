import re
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath

import yaml
from pytest import mark, raises

from gitmentario.models import Comment
from gitmentario.ssg import escape_shortcodes, prepare_comment_markdown
from gitmentario.utils import FALLBACK_NAME

CONTENT_DIR = PurePosixPath("content")
COMMENTS_DIR = PurePosixPath("comments")

LIVE_OPENER = re.compile(r"\{\{[<%](?!/\*)")

FILENAME = re.compile(r"^\d{14}_(?P<name>.+)\.md$")


def prepare(**overrides: str) -> tuple[str, str]:
    """Run the production path with a valid comment, varying one field."""
    fields: dict[str, str] = {
        "author": "Test",
        "message": "hello",
        "page_id": "real-post",
    }
    comment = Comment(**{**fields, **overrides})
    return prepare_comment_markdown(comment, CONTENT_DIR, COMMENTS_DIR)


def frontmatter_of(md_content: str) -> dict[str, str]:
    """Parse the YAML frontmatter block back out of the generated file."""
    _, _, rest = md_content.partition("---\n")
    block, _, _ = rest.partition("---\n")
    parsed = yaml.safe_load(block)
    assert isinstance(parsed, dict)
    return parsed


def body_of(md_content: str) -> str:
    """Return everything after the frontmatter block, trailing newline included."""
    _, _, body = md_content.partition("---\n\n")
    return body


# file path
def test_path_is_composed_of_the_configured_parts() -> None:
    file_path, _ = prepare(page_id="my-post", archetype="posts")
    path = PurePosixPath(file_path)
    assert path.parent == PurePosixPath("content/posts/my-post/comments")
    assert FILENAME.match(path.name), path.name


@mark.parametrize(
    "page_id", ["real-post", "a/b/c", "2026/09/my-post", "post.with.dots"]
)
def test_path_stays_under_the_content_directory(page_id: str) -> None:
    file_path, _ = prepare(page_id=page_id)
    assert PurePosixPath(file_path).is_relative_to(CONTENT_DIR)


def test_filename_carries_the_sanitized_author() -> None:
    file_path, _ = prepare(author="Ada Lovelace")
    match = FILENAME.match(PurePosixPath(file_path).name)
    assert match is not None
    assert match["name"] == "Ada_Lovelace"


def test_filename_timestamp_is_utc_now() -> None:
    """A stale or local-time stamp would collide or order comments wrongly."""
    before = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    file_path, _ = prepare()
    after = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    stamp = PurePosixPath(file_path).name[:14]
    assert before <= stamp <= after


@mark.parametrize("author", ["日本語", "Дмитрий", "...", "  ' "])
def test_unusable_author_falls_back_in_the_filename(author: str) -> None:
    """A name in a non-Latin script must not fail the request."""
    file_path, _ = prepare(author=author)
    match = FILENAME.match(PurePosixPath(file_path).name)
    assert match is not None
    assert match["name"] == FALLBACK_NAME


# containment, independent of the model
@mark.parametrize("page_id", ["/absolute", "../../..", "a/../../b"])
def test_escaping_page_id_rejected_even_if_the_model_is_bypassed(
    page_id: str,
) -> None:
    """The writer must not depend on Comment having validated its input.

    `Comment` already rejects these, so the assertion is unreachable through the
    API. Setting the attribute directly is the only way to prove the second line
    of defence is actually wired up.
    """
    _, md = prepare()
    comment = Comment(author="Test", message="hello", page_id="placeholder")
    object.__setattr__(comment, "page_id", page_id)
    with raises(ValueError):
        prepare_comment_markdown(comment, CONTENT_DIR, COMMENTS_DIR)
    assert md  # the valid case above really does succeed


def test_escaping_archetype_rejected_even_if_the_model_is_bypassed() -> None:
    comment = Comment(author="Test", message="hello", page_id="real-post")
    object.__setattr__(comment, "archetype", "../..")
    with raises(ValueError):
        prepare_comment_markdown(comment, CONTENT_DIR, COMMENTS_DIR)


# frontmatter
def test_frontmatter_records_author_and_date() -> None:
    _, md_content = prepare(author="Ada Lovelace")
    frontmatter = frontmatter_of(md_content)
    assert frontmatter["author"] == "Ada Lovelace"
    assert frontmatter["date"].endswith("Z")


def test_frontmatter_date_is_a_parsable_utc_timestamp() -> None:
    """A malformed date fails the SSG build for the whole site.

    Checking only the `Z` suffix is not enough: an aware `isoformat()` plus a
    literal `Z` yields `+00:00Z`, which ends in `Z`, parses nowhere, and made
    Hugo reject every comment.
    """
    _, md_content = prepare()
    parsed = datetime.fromisoformat(frontmatter_of(md_content)["date"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)
    assert abs((datetime.now(UTC) - parsed).total_seconds()) < 60


@mark.parametrize("author", ["日本語", "Дмитрий", "Ada Lovelace", 'quote"and:colon'])
def test_frontmatter_round_trips_the_author_verbatim(author: str) -> None:
    """The display name is preserved even when the filename cannot keep it."""
    _, md_content = prepare(author=author)
    assert frontmatter_of(md_content)["author"] == author


def test_frontmatter_keeps_non_latin_readable() -> None:
    """Escaped sequences would be valid YAML but unreadable in review."""
    _, md_content = prepare(author="日本語")
    assert "日本語" in md_content


def test_frontmatter_injection_is_not_possible() -> None:
    """A crafted author must stay one YAML value, not add keys."""
    _, md_content = prepare(author="x\ndraft: true")
    assert frontmatter_of(md_content) == {
        "author": "x\ndraft: true",
        "date": frontmatter_of(md_content)["date"],
    }


# body
def test_body_holds_the_message() -> None:
    _, md_content = prepare(message="Nice post!")
    assert body_of(md_content) == "Nice post!\n"


def test_ordinary_markdown_is_written_verbatim() -> None:
    """Escaping must not quietly become general sanitization."""
    message = "Nice post!\n\n- one\n- two\n\n`code` and <em>html</em>"
    _, md_content = prepare(message=message)
    assert body_of(md_content) == f"{message}\n"


# shortcode escaping
@mark.parametrize(
    ("raw", "expected"),
    [
        ('{{< ref "post" >}}', '{{</* ref "post" */>}}'),
        ("{{% note %}}", "{{%/* note */%}}"),
        ("a {{< x >}} b {{< y >}} c", "a {{</* x */>}} b {{</* y */>}} c"),
        ("{{< multi\nline >}}", "{{</* multi\nline */>}}"),
        # Already-escaped input must not be escaped a second time.
        ("{{</* already */>}}", "{{</* already */>}}"),
        ("{{%/* already */%}}", "{{%/* already */%}}"),
        # Not shortcode syntax, so left alone.
        ("{{ plain }} and { { no", "{{ plain }} and { { no"),
        ("normal comment text", "normal comment text"),
    ],
)
def test_shortcodes_escaped_to_hugo_literal_form(raw: str, expected: str) -> None:
    assert escape_shortcodes(raw) == expected


@mark.parametrize(
    "raw",
    [
        # An unpaired opener has no escaped form; Hugo rejects it as unclosed.
        "{{< unclosed",
        "{{% unclosed",
        # Attempts to slip a live opener past the paired-shortcode rewrite.
        "*/>}}{{< evil >}}",
        "{{<x*/>}}",
        "{{< a {{< b >}} >}}",
        "{{</*fake*/>}}{{< evil >}}",
        "{{<{{< nested >}}",
        "{{%/* x */%}}{{% evil %}}",
    ],
)
def test_no_live_delimiter_survives(raw: str) -> None:
    assert not LIVE_OPENER.search(escape_shortcodes(raw))


def test_escaping_is_idempotent() -> None:
    """Re-running must not accumulate comment markers."""
    once = escape_shortcodes('{{< ref "x" >}} and {{< broken')
    assert escape_shortcodes(once) == once


def test_escaping_applied_to_the_written_comment() -> None:
    _, md_content = prepare(message='see {{< ref "x" >}} and {{< broken')
    assert not LIVE_OPENER.search(md_content)
    assert '{{</* ref "x" */>}}' in md_content
