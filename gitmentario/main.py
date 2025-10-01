from datetime import datetime
from logging import Formatter, StreamHandler, getLogger
from sys import stdout

import gitlab
import gitlab.v4.objects
from fastapi import FastAPI, HTTPException

from .helpers import safe_name
from .models import Comment
from .settings import get_settings
from .ssg import prepare_comment_markdown

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


def get_gitlab_project() -> gitlab.v4.objects.Project:
    """Return the configured GitLab project instance."""
    gl = gitlab.Gitlab(settings.gitlab_url, private_token=settings.gitlab_token)
    return gl.projects.get(settings.gitlab_project_id)


def check_file_exists(
    project: gitlab.v4.objects.Project, branch: str, filename: str
) -> None:
    """Raise HTTPException if the file already exists on the given branch."""
    try:
        project.files.get(file_path=filename, ref=branch)
        raise HTTPException(status_code=409, detail="Comment already exists.")
    except gitlab.exceptions.GitlabGetError:
        return  # File does not exist, continue


def create_file(
    project: gitlab.v4.objects.Project,
    branch: str,
    filename: str,
    file_content: str,
    name: str,
) -> None:
    """Create a file in the given branch with commit message."""
    try:
        project.files.create(
            {
                "file_path": filename,
                "branch": branch,
                "content": file_content,
                "commit_message": f"Add comment from {name}",
            }
        )
    except gitlab.exceptions.GitlabCreateError as exc:
        logger.error(
            "Failed to create file '%s' in branch '%s': %s", filename, branch, exc
        )
        raise HTTPException(status_code=500, detail="Failed to create comment.")


def git_push_to_default_branch(filename: str, file_content: str, name: str) -> None:
    """Directly push a file to the project's default branch."""
    logger.debug("Push '%s' to default branch.", filename)
    project = get_gitlab_project()
    default_branch = project.default_branch

    check_file_exists(project, default_branch, filename)
    create_file(project, default_branch, filename, file_content, name)


def git_create_branch_and_mr(filename: str, file_content: str, name: str) -> None:
    """Create a new branch, push the file, and open a merge request."""
    project = get_gitlab_project()

    check_file_exists(project, settings.target_branch, filename)

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    branch_name = f"gitmentario-{timestamp}-{safe_name(name)}".lower()

    try:
        project.branches.create({"branch": branch_name, "ref": settings.target_branch})
    except gitlab.exceptions.GitlabCreateError as exc:
        logger.error("Failed to create branch '%s': %s", branch_name, exc)
        raise HTTPException(status_code=500, detail="Failed to create comment.")

    create_file(project, branch_name, filename, file_content, name)

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
    """Add a new comment."""
    filename, file_content = prepare_comment_markdown(
        comment, settings.content_dir, settings.comments_dir
    )
    if settings.git_push:
        git_push_to_default_branch(filename, file_content, comment.author)
    else:
        git_create_branch_and_mr(filename, file_content, comment.author)

    return {"status": "success"}
