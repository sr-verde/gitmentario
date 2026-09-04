from functools import cache
from pathlib import PurePosixPath
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AnyHttpUrl,
    BeforeValidator,
    PositiveInt,
    SecretStr,
    constr,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from gitmentario.utils import check_repo_relative


def _split_origins(value: object) -> object:
    """Accept a comma-separated list of origins, as written in a ``.env`` file."""
    if isinstance(value, str):
        return tuple(
            origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()
        )
    return value


Origins = Annotated[tuple[str, ...], NoDecode, BeforeValidator(_split_origins)]
"""Browser origins permitted to submit comments.

A tuple rather than a list or set: ``CORSMiddleware`` declares ``Sequence[str]``
(so a set does not type-check), and ``get_settings`` is cached, so an immutable
value avoids sharing mutable state process-wide.

Kept as plain strings rather than URLs: a browser sends ``Origin`` without a
trailing slash, which a parsed URL type would add back and so never match.
``NoDecode`` opts out of the JSON decoding pydantic-settings applies to
collection fields, so ``.env`` can use a readable comma-separated value.
"""

RepoPath = Annotated[PurePosixPath, AfterValidator(check_repo_relative)]
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

    allowed_origins: Origins = ()
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
