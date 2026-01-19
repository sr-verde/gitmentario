from abc import ABC, abstractmethod
from datetime import date

from gitmentario.exceptions import BranchExistsError
from gitmentario.utils import safe_name


def create_mr_title(name: str) -> str:
    """Return a standardized merge/pull request title.

    Args:
        name (str): Context-specific identifier.

    Returns:
        str: Generated MR title.
    """
    return f"💬 Add comment from {name}"


def create_commit_message(name: str) -> str:
    """Return a standardized commit message.

    Args:
        name (str): Context-specific identifier.

    Returns:
        str: Commit message.
    """
    return create_mr_title(name)


def create_branch_name(name: str, suffix: str | int = None) -> str:
    """Return a standardized branch name.

    Args:
        name (str): Context-specific identifier.
        suffix (str | None): Suffix to be added

    Returns:
        str: Branch name.
    """
    if suffix:
        name = f"{name}-{suffix}"
    date_str = date.today().strftime("%Y-%m-%d")
    return f"{safe_name(name, '-')}-{date_str}"


class ForgeClient(ABC):
    """Abstract base class that defines an interface for interacting with Git forges such as GitLab or GitHub.

    Implementations should provide forge-specific logic for managing files and creating pull/merge requests
    using the forge's API. This interface enables unified handling of repository operations regardless of the
    underlying forge implementation.
    """

    @abstractmethod
    def get_default_branch(self) -> str:
        """Return the repository's default branch name.

        Returns:
            str: Default branch name.
        """
        ...

    @abstractmethod
    def get_target_branch(self) -> str:
        """Return the target branch for merge requests.

        Returns:
            str: Target branch name.
        """
        ...

    @abstractmethod
    def check_file_exists(self, branch: str, filename: str) -> None:
        """Check whether a file exists in the given branch.

        Args:
            branch (str): Name of the branch to search in.
            filename (str): Path to the file within the repository.

        Raises:
            HTTPException: If the file already exists and the action should not proceed.
        """
        ...

    def push_to_default_branch(
        self, filename: str, file_content: str, name: str
    ) -> None:
        """Workflow to push a comment file to the repository's default branch.

        Standardizes naming and delegates forge-specific logic.

        Args:
            filename (str): Path of the file to add.
            file_content (str): Content to write to the file.
            name (str): Name to include in the commit message or author information.

        Raises:
            HTTPException: If file creation or push fails.
        """
        commit_message = create_commit_message(name)
        default_branch = self.get_default_branch()
        self._push_file_to_branch(
            default_branch, filename, file_content, commit_message
        )

    def create_branch_and_mr(self, filename: str, file_content: str, name: str) -> None:
        """Workflow to create a branch, add a comment file, and open a MR/PR.

        Standardizes naming and delegates forge-specific logic.

        Args:
            filename (str): Path of the file to add.
            file_content (str): Content to write to the new file.
            name (str): Name to use for branch identification and in the commit/MR/PR.

        Raises:
            HTTPException: If branch creation, file addition, or MR/PR fails.
        """
        commit_message = create_commit_message(name)
        mr_title = create_mr_title(name)
        target_branch = self.get_target_branch()
        suffix = None
        while True:
            branch_name = create_branch_name(name, suffix=suffix)
            try:
                self._create_branch_and_mr(
                    branch_name,
                    target_branch,
                    filename,
                    file_content,
                    commit_message,
                    mr_title,
                )
                break
            except BranchExistsError:
                if not suffix:
                    suffix = 1
                else:
                    suffix += 1

    @abstractmethod
    def _push_file_to_branch(
        self, branch: str, filename: str, file_content: str, commit_message: str
    ) -> None:
        """Subclass must implement platform-specific logic for pushing a file to a branch."""
        ...

    @abstractmethod
    def _create_branch_and_mr(  # noqa: PLR0913
        self,
        branch: str,
        target_branch: str,
        filename: str,
        file_content: str,
        commit_message: str,
        mr_title: str,
    ) -> None:
        """Subclass must implement platform-specific logic for branch creation, file addition, and MR/PR creation."""
        ...
