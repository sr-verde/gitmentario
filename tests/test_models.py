from pathlib import PurePosixPath

from pydantic import ValidationError
from pytest import mark, raises

from gitmentario.models import Comment
from gitmentario.ssg import prepare_comment_markdown
from gitmentario.utils import FALLBACK_NAME


def make_comment(page_id: str) -> Comment:
    return Comment(author="Test", message="hello", page_id=page_id)


@mark.parametrize(
    "page_id", ["real-post", "a/b/c", "2026/09/my-post", "post.with.dots"]
)
def test_valid_page_ids_accepted(page_id: str) -> None:
    assert make_comment(page_id).page_id == page_id


@mark.parametrize(
    "page_id",
    [
        "/absolute",
        "/",
        "/content",
        "../../..",
        "a/../../b",
        "..",
        "a//b",
        "a/./b",
        "trailing/",
        "with\nnewline",
        "nul\x00byte",
        "tab\there",
    ],
)
def test_unsafe_page_ids_rejected(page_id: str) -> None:
    with raises(ValidationError):
        make_comment(page_id)


@mark.parametrize("page_id", ["real-post", "a/b/c", "2026/09/my-post"])
def test_comment_path_stays_under_content_dir(page_id: str) -> None:
    content_dir = PurePosixPath("content")
    file_path, _ = prepare_comment_markdown(
        make_comment(page_id), content_dir, PurePosixPath("comments")
    )
    assert PurePosixPath(file_path).is_relative_to(content_dir)


@mark.parametrize("page_id", ["/absolute", "../../..", "a/../../b"])
def test_escaping_path_rejected_even_if_model_bypassed(page_id: str) -> None:
    """prepare_comment_markdown must not rely on Comment having validated page_id."""
    comment = make_comment("placeholder")
    object.__setattr__(comment, "page_id", page_id)
    with raises(ValueError):
        prepare_comment_markdown(
            comment, PurePosixPath("content"), PurePosixPath("comments")
        )


def test_escaping_archetype_rejected_even_if_model_bypassed() -> None:
    comment = make_comment("real-post")
    object.__setattr__(comment, "archetype", "../..")
    with raises(ValueError):
        prepare_comment_markdown(
            comment, PurePosixPath("content"), PurePosixPath("comments")
        )


@mark.parametrize("author", ["日本語", "Дмитрий", "...", "  ' "])
def test_non_latin_author_does_not_raise(author: str) -> None:
    comment = Comment(author=author, message="hello", page_id="real-post")
    file_path, md_content = prepare_comment_markdown(
        comment, PurePosixPath("content"), PurePosixPath("comments")
    )
    assert file_path.endswith(f"_{FALLBACK_NAME}.md")
    # The real name is still recorded verbatim in the frontmatter.
    assert author.strip() in md_content
