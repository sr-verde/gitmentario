from pathlib import PurePosixPath

from pydantic import ValidationError
from pytest import mark, raises

from gitmentario.models import Comment
from gitmentario.ssg import prepare_comment_markdown


def make_comment(page_id: str) -> Comment:
    return Comment(author="Test", message="hello", page_id=page_id)


@mark.parametrize("page_id", ["real-post", "a/b/c", "2026/09/my-post", "post.with.dots"])
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
