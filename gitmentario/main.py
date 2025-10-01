import os
from datetime import datetime
from logging import Formatter, StreamHandler, getLogger
from sys import stdout

import gitlab
import yaml
from fastapi import FastAPI, HTTPException

from .helpers import safe_name
from .models import Comment
from .settings import get_settings

settings = get_settings()

logger = getLogger(__name__)
logger.setLevel(settings.log_level)
stream_handler = StreamHandler(stdout)
log_formatter = Formatter(
    "%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s"
)
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)

logger.info("API is starting up.")


def prepare_comment_markdown(
    comment: Comment, content_dir: str, comments_dir: str
) -> tuple[str, str]:
    abs_comments_dir = os.path.join(
        content_dir, comment.archetype, comment.page_id, comments_dir
    )
    os.makedirs(abs_comments_dir, exist_ok=True)
    timestamp = datetime.utcnow()
    name = safe_name(comment.author)
    filename = os.path.join(
        abs_comments_dir, f"{timestamp.strftime('%Y%m%d%H%M%S')}_{name}.md"
    )
    frontmatter = yaml.safe_dump(
        {"author": comment.author, "date": timestamp.isoformat() + "Z"},
        sort_keys=False,
        default_flow_style=False,
    )
    md_content = f"---\n{frontmatter}---\n\n{comment.message}\n"
    return (filename, md_content)


def git_push_to_default_branch(
    filename: str,
    file_content: str,
    name: str,
) -> None:
    logger.debug("Push '%s' to default branch.", filename)
    gl = gitlab.Gitlab("https://gitlab.com", private_token=settings.gitlab_token)
    project = gl.projects.get(settings.gitlab_project_id)

    # Get default branch of the project
    default_branch = project.default_branch

    # Check if file already exists on default branch
    try:
        _ = project.files.get(file_path=filename, ref=default_branch)
        raise HTTPException(status_code=409, detail="Comment already exists.")
    except gitlab.exceptions.GitlabGetError:
        # File does not exist on default branch, continue
        pass

    # Create the file on the default branch directly
    try:
        project.files.create(
            {
                "file_path": filename,
                "branch": default_branch,
                "content": file_content,
                "commit_message": f"Add comment from {name}",
            }
        )
    except gitlab.exceptions.GitlabCreateError as exc:
        logger.error("Failed to create file '%s' on default branch: %s", filename, exc)
        raise HTTPException(status_code=500, detail="Failed to create comment.")


def git_create_branch_and_mr(
    filename: str,
    file_content: str,
    name: str,
) -> None:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    branch_name = f"gitmentario-{timestamp}-{safe_name(name)}".lower()

    gl = gitlab.Gitlab("https://gitlab.com", private_token=settings.gitlab_token)
    project = gl.projects.get(settings.gitlab_project_id)

    # Check if file already exists on target branch (to avoid conflict)
    try:
        _ = project.files.get(file_path=filename, ref=settings.target_branch)
        # If no exception, file exists, so raise conflict
        raise HTTPException(status_code=409, detail="Comment already exists.")
    except gitlab.exceptions.GitlabGetError:
        # File does not exist on target branch, proceed
        pass

    # Create a new branch from the target branch
    try:
        project.branches.create({"branch": branch_name, "ref": settings.target_branch})
    except gitlab.exceptions.GitlabCreateError as exc:
        logger.error("Failed to create branch '%s': %s", branch_name, exc)
        raise HTTPException(status_code=500, detail="Failed to create comment.")

    # Create the file on the new branch
    try:
        project.files.create(
            {
                "file_path": filename,
                "branch": branch_name,
                "content": file_content,
                "commit_message": f"Add comment from {name}",
            }
        )
    except gitlab.exceptions.GitlabCreateError as exc:
        logger.error(
            "Failed to create file '%s' in branch '%s': %s", filename, branch_name, exc
        )
        raise HTTPException(status_code=500, detail="Failed to create comment.")

    # Create merge request
    mr_title = f"💬 Add comment from {name}"
    project.mergerequests.create(
        {
            "source_branch": branch_name,
            "target_branch": settings.target_branch,
            "title": mr_title,
        }
    )


# FastAPI App
app = FastAPI()


@app.post("/comment")
async def add_comment(comment: Comment):
    filename, file_content = prepare_comment_markdown(
        comment, settings.content_dir, settings.comments_dir
    )
    if settings.git_push:
        git_push_to_default_branch(filename, file_content, comment.author)
    else:
        git_create_branch_and_mr(filename, file_content, comment.author)

    return {"status": "success"}
