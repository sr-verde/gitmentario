import gitlab
from fastapi import HTTPException

from gitmentario.forge import ForgeClient


class GitlabClient(ForgeClient):
    """GitLab client for managing file operations, branch creation, and merge requests using the GitLab API.

    Subclass of ForgeClient providing forge-specific logic.

    Attributes:
        gitlab_instance (gitlab.Gitlab): GitLab API client.
        project (gitlab.v4.objects.Project): Project object.
        settings (object): Settings/configuration.
        logger (logging.Logger): Logger for diagnostics.
    """

    def __init__(self, settings, logger):
        """Initialize the GitLab client for a specific repository.

        Args:
            settings (object): Config containing gitlab_url, gitlab_token, gitlab_project_id, target_branch.
            logger (logging.Logger): Log handler.
        """
        self.gitlab_instance = gitlab.Gitlab(
            str(settings.base_url), private_token=settings.auth_token.get_secret_value()
        )
        self.project = self.gitlab_instance.projects.get(settings.project_id)
        self.settings = settings
        self.logger = logger

    def get_default_branch(self) -> str:
        """Return the repository's default branch name.

        Returns:
            str: Default branch name.
        """
        return self.project.default_branch

    def get_target_branch(self) -> str:
        """Return the target branch for merge requests.

        Returns:
            str: Target branch name.
        """
        return self.settings.target_branch

    def check_file_exists(self, branch: str, filename: str) -> None:
        """Check if a file exists in the given branch.

        Args:
            branch (str): Branch name.
            filename (str): File path.

        Raises:
            HTTPException: If the file already exists.
        """
        try:
            self.project.files.get(file_path=filename, ref=branch)
            raise HTTPException(status_code=409, detail="Comment already exists.")
        except gitlab.exceptions.GitlabGetError:
            return None

    def _push_file_to_branch(
        self, branch: str, filename: str, file_content: str, commit_message: str
    ) -> None:
        """Create a file in the specified branch with the provided commit message.

        Args:
            branch (str): Branch name.
            filename (str): File path.
            file_content (str): Content to write.
            commit_message (str): Commit message.

        Raises:
            HTTPException: If file creation fails.
        """
        self.logger.debug("Push '%s' to branch '%s'.", filename, branch)
        self.check_file_exists(branch, filename)
        try:
            self.project.files.create(
                {
                    "file_path": filename,
                    "branch": branch,
                    "content": file_content,
                    "commit_message": commit_message,
                }
            )
        except gitlab.exceptions.GitlabCreateError as exc:
            self.logger.error(
                "Failed to create file '%s' in branch '%s': %s", filename, branch, exc
            )
            raise HTTPException(
                status_code=500, detail="Failed to create comment."
            ) from exc

    def _create_branch_and_mr(  # noqa: PLR0913
        self,
        branch_name: str,
        target_branch: str,
        filename: str,
        file_content: str,
        commit_message: str,
        mr_title: str,
    ) -> None:
        """Create a new branch from target, push the file, and open a merge request.

        Args:
            branch_name (str): Name of new branch.
            target_branch (str): Target branch for MR.
            filename (str): File path to add.
            file_content (str): Content to write.
            commit_message (str): Commit message.
            mr_title (str): MR title.

        Raises:
            HTTPException: On failure to create branch, file, or MR.
        """
        self.check_file_exists(target_branch, filename)
        try:
            self.project.branches.create({"branch": branch_name, "ref": target_branch})
        except gitlab.exceptions.GitlabCreateError as exc:
            self.logger.error("Failed to create branch '%s': %s", branch_name, exc)
            raise exc
