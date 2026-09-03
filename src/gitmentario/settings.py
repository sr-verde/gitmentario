from functools import cache
from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import AfterValidator, AnyHttpUrl, PositiveInt, SecretStr, constr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _must_be_relative(path: PurePosixPath) -> PurePosixPath:
    """Reject absolute paths and paths escaping the repository root."""
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("must be a relative path without '..' segments")
    return path


RepoPath = Annotated[PurePosixPath, AfterValidator(_must_be_relative)]
"""A path inside the repository, always with forward slashes.

Forge APIs address files by repo-relative POSIX path, so this stays
``PurePosixPath`` on every host platform and is never touched on disk.
"""


class ForgeConfig(BaseSettings):
    """Configuration of the forge to be used."""

    type: Literal["gitlab"]
    auth_token: SecretStr
    project_id: PositiveInt
    base_url: AnyHttpUrl


class Settings(BaseSettings):
    """Configuration settings for the API.

    This class defines all the necessary settings for the API, including logging,
    and external service URLs. It uses Pydantic's BaseSettings for automatic
    environment variable loading and validation.

    Note:
        For more information on Pydantic settings, see:
            https://docs.pydantic.dev/latest/concepts/pydantic_settings/
    """

    comments_dir: RepoPath = PurePosixPath("comments")
    content_dir: RepoPath

    git_push: bool = True  # True = direkt pushen, False = MR erstellen

    forge: ForgeConfig

    target_branch: str = "main"
    log_level: Annotated[
        Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        constr(to_upper=True, strip_whitespace=True),
    ] = "INFO"

    # Model config: https://docs.pydantic.dev/2.6/api/config/#pydantic.config.ConfigDict
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
    )


@cache
def get_settings() -> Settings:
    """Retrieve a cached instance of the Settings.

    This function uses the lru_cache decorator to cache the Settings instance,
    avoiding repeated I/O operations when accessing configuration settings.

    Returns:
        Settings: A cached instance of the Settings class.

    Note:
        The caching mechanism assumes that the settings do not change during
        the lifetime of the application. If dynamic configuration updates are
        required, consider using a different caching strategy.

    """
    return Settings()
