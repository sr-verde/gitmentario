from pytest import MonkeyPatch, mark

from gitmentario.settings import Settings

REQUIRED_ENV = {
    "CONTENT_DIR": "content",
    "FORGE__TYPE": "gitlab",
    "FORGE__AUTH_TOKEN": "token",
    "FORGE__PROJECT_ID": "1",
    "FORGE__BASE_URL": "https://gitlab.example.com",
}


def build_settings(monkeypatch: MonkeyPatch, **env: str) -> Settings:
    for key, value in {**REQUIRED_ENV, **env}.items():
        monkeypatch.setenv(key, value)
    # _env_file=None so a developer's local .env cannot influence the result
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_allowed_origins_defaults_to_empty(monkeypatch: MonkeyPatch) -> None:
    assert build_settings(monkeypatch).allowed_origins == ()


@mark.parametrize(
    ("raw", "expected"),
    [
        ("https://example.com", ("https://example.com",)),
        (
            "https://example.com,https://www.example.com",
            ("https://example.com", "https://www.example.com"),
        ),
        # Whitespace around entries is tolerated
        (
            "https://example.com , https://www.example.com",
            ("https://example.com", "https://www.example.com"),
        ),
        # A browser sends Origin without a trailing slash, so one must be stripped
        ("https://example.com/", ("https://example.com",)),
        ("", ()),
    ],
)
def test_allowed_origins_parsed_from_comma_separated_env(
    monkeypatch: MonkeyPatch, raw: str, expected: tuple[str, ...]
) -> None:
    settings = build_settings(monkeypatch, ALLOWED_ORIGINS=raw)
    assert settings.allowed_origins == expected
