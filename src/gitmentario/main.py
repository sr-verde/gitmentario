from logging import Formatter, StreamHandler, getLogger
from sys import stdout

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .forge.base import ForgeClient
from .forge.gitlab import GitlabClient
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

forge_client: ForgeClient
if settings.forge.type == "gitlab":
    forge_client = GitlabClient(settings.forge, settings.target_branch, logger)

app = FastAPI()

if settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
    )
else:
    logger.warning(
        "ALLOWED_ORIGINS is empty; browsers will refuse to submit comments "
        "cross-origin. Set it to the origin of your website."
    )


@app.post("/comment")
async def add_comment(comment: Comment):
    """Add a new comment."""
    filename, file_content = prepare_comment_markdown(
        comment, settings.content_dir, settings.comments_dir
    )
    if settings.git_push:
        forge_client.push_to_default_branch(filename, file_content, comment.author)
    else:
        forge_client.create_branch_and_mr(filename, file_content, comment.author)

    return {"status": "success"}
