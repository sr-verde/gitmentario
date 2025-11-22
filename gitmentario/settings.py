from functools import cache
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, PositiveInt, SecretStr, constr
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    repo_path: str = "."
    comments_dir: str = "comments"
    content_dir: str

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
