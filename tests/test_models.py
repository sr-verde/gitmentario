from pydantic import ValidationError
from pytest import mark, raises

from gitmentario.models import Comment

AUTHOR_MAX = 64
MESSAGE_MAX = 1024
ARCHETYPE_MAX = 32
PAGE_ID_MAX = 1024

REQUIRED_FIELDS = {"author": "Test", "message": "hello", "page_id": "real-post"}


def make_comment(**overrides: str) -> Comment:
    """Build a valid comment, so each test varies only the field it is about."""
    return Comment(**{**REQUIRED_FIELDS, **overrides})


def test_defaults_applied() -> None:
    assert make_comment().archetype == "default"


@mark.parametrize("field", sorted(REQUIRED_FIELDS))
def test_required_fields_must_be_given(field: str) -> None:
    fields = dict(REQUIRED_FIELDS)
    del fields[field]
    with raises(ValidationError):
        Comment(**fields)


@mark.parametrize(
    ("field", "value", "expected"),
    [
        ("author", "  Test  ", "Test"),
        ("message", "  hello  ", "hello"),
        ("page_id", "  real-post  ", "real-post"),
        ("archetype", "  posts  ", "posts"),
    ],
)
def test_surrounding_whitespace_is_stripped(
    field: str, value: str, expected: str
) -> None:
    assert getattr(make_comment(**{field: value}), field) == expected


@mark.parametrize(
    ("field", "limit"),
    [
        ("author", AUTHOR_MAX),
        ("message", MESSAGE_MAX),
        ("archetype", ARCHETYPE_MAX),
        ("page_id", PAGE_ID_MAX),
    ],
)
def test_field_accepts_its_maximum_length(field: str, limit: int) -> None:
    assert len(getattr(make_comment(**{field: "a" * limit}), field)) == limit


@mark.parametrize(
    ("field", "limit"),
    [
        ("author", AUTHOR_MAX),
        ("message", MESSAGE_MAX),
        ("archetype", ARCHETYPE_MAX),
        ("page_id", PAGE_ID_MAX),
    ],
)
def test_field_rejects_one_over_its_maximum(field: str, limit: int) -> None:
    with raises(ValidationError):
        make_comment(**{field: "a" * (limit + 1)})


@mark.parametrize("field", ["author", "message", "archetype", "page_id"])
@mark.parametrize("value", ["", "   "])
def test_field_rejects_empty_value(field: str, value: str) -> None:
    with raises(ValidationError):
        make_comment(**{field: value})


@mark.parametrize("archetype", ["posts", "default", "Notes", "日本語"])
def test_alphabetic_archetypes_accepted(archetype: str) -> None:
    assert make_comment(archetype=archetype).archetype == archetype


@mark.parametrize("archetype", ["posts2", "with space", "with-dash", "a/b", "a.b"])
def test_non_alphabetic_archetypes_rejected(archetype: str) -> None:
    with raises(ValidationError):
        make_comment(archetype=archetype)


@mark.parametrize(
    "page_id", ["real-post", "a/b/c", "2026/09/my-post", "post.with.dots", "a_b"]
)
def test_valid_page_ids_accepted(page_id: str) -> None:
    assert make_comment(page_id=page_id).page_id == page_id


@mark.parametrize("page_id", ["café", "日本語", "naïve"])
def test_non_ascii_page_ids_rejected(page_id: str) -> None:
    with raises(ValidationError):
        make_comment(page_id=page_id)


@mark.parametrize(
    "page_id",
    [
        # An absolute path discards the content directory entirely when joined.
        "/absolute",
        "/",
        "/content",
        # Traversal out of the content directory.
        "../../..",
        "a/../../b",
        "..",
        # Segments that normalize unpredictably.
        "a//b",
        "a/./b",
        "trailing/",
        # Control characters would also forge log lines.
        "with\nnewline",
        "nul\x00byte",
        "tab\there",
        "carriage\rreturn",
    ],
)
def test_unsafe_page_ids_rejected(page_id: str) -> None:
    with raises(ValidationError):
        make_comment(page_id=page_id)


def test_message_may_contain_markup_and_newlines() -> None:
    """A comment body is data; what is safe to render is the SSG’s concern."""
    message = "Line one\n\n<em>html</em> & `code`"
    assert make_comment(message=message).message == message
