from datetime import datetime
from pathlib import PurePosixPath

import yaml

from .models import Comment
from .utils import safe_name


def prepare_comment_markdown(
    comment: Comment, content_dir: PurePosixPath, comments_dir: PurePosixPath
) -> tuple[str, str]:
    """Generate a Markdown file representation of a comment with YAML frontmatter.

    Creates a unique filename using the current UTC timestamp and a sanitized
    author name, and formats the comment data into Markdown with a YAML
    frontmatter block. Returns the repo-relative file path and the Markdown
    content as a string; does not touch the local filesystem.

    Args:
        comment (Comment): The comment object containing at least `author`,
            `message`, `archetype`, and `page_id` attributes.
        content_dir (PurePosixPath): Repo-relative path to the content directory
            of the website.
        comments_dir (PurePosixPath): Subdirectory under the page where comments
            are stored.

    Returns:
        tuple[str, str]: A tuple containing:
            - The repo-relative Markdown file path (str).
            - The Markdown content with YAML frontmatter (str).
    """
    comments_dir_path = content_dir / comment.archetype / comment.page_id / comments_dir
    timestamp = datetime.utcnow()
    name = safe_name(comment.author)
    file_path = comments_dir_path / f"{timestamp.strftime('%Y%m%d%H%M%S')}_{name}.md"
    frontmatter = yaml.safe_dump(
        {"author": comment.author, "date": timestamp.isoformat() + "Z"},
        sort_keys=False,
        default_flow_style=False,
    )
    md_content = f"---\n{frontmatter}---\n\n{comment.message}\n"
    return (str(file_path), md_content)
