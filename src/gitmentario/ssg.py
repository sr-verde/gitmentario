import os
from datetime import datetime

import yaml

from .models import Comment
from .utils import safe_name


def prepare_comment_markdown(
    comment: Comment, content_dir: str, comments_dir: str
) -> tuple[str, str]:
    """Generate a Markdown file representation of a comment with YAML frontmatter.

    This function ensures the target directory exists, creates a unique filename
    using the current UTC timestamp and a sanitized author name, and formats
    the comment data (author, timestamp, message) into Markdown with a YAML
    frontmatter block. It does not write the file to disk, but instead returns
    the absolute file path and the Markdown content as a string.

    Args:
        comment (Comment): The comment object containing at least `author`,
            `message`, `archetype`, and `page_id` attributes.
        content_dir (str): Base content directory of the website.
        comments_dir (str): Subdirectory under the page where comments are stored.

    Returns:
        tuple[str, str]: A tuple containing:
            - The absolute Markdown file path (str).
            - The Markdown content with YAML frontmatter (str).
    """
    abs_comments_dir = os.path.join(
        content_dir, comment.archetype, comment.page_id, comments_dir
    )
    os.makedirs(abs_comments_dir, exist_ok=True)
    timestamp = datetime.utcnow()
    name = safe_name(comment.author)
    file_path = os.path.join(
        abs_comments_dir, f"{timestamp.strftime('%Y%m%d%H%M%S')}_{name}.md"
    )
    frontmatter = yaml.safe_dump(
        {"author": comment.author, "date": timestamp.isoformat() + "Z"},
        sort_keys=False,
        default_flow_style=False,
    )
    md_content = f"---\n{frontmatter}---\n\n{comment.message}\n"
    return (file_path, md_content)
