# Gitmentario

Gitmentario is a comment service for websites built with Static Site Generators (SSG).
Comments are pushed as Markdown resources into your website’s Git repository.

## Supported Platforms

Gitmentario currently only supports [Hugo](https://gohugo.io) as SSG and Gitlab as software forge.
At least Jekyll and Github are planned to be supported, too.

## Features

- Comments are true resources of your website
- No vendor lock-in: you don’t lose your comments when switching approaches
- Comment moderation via merge requests
- Minimal JavaScript footprint

## How It Works

1. A visitor writes a comment on your website
2. A small JavaScript snippet sends the data to Gitmentario
3. Gitmentario creates a Markdown file from the comment
4. The service either:
   - pushes the Markdown file directly to the default branch (`GIT_PUSH=true`)
   - creates a new branch with the file and opens a merge request (`GIT_PUSH=false`)

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Usage

### Run directly

```bash
fastapi run src/gitmentario/main.py
```

### Run with Docker Compose

You can use e.g. Docker to run Gitmentario.
Copy `compose.yml` and adjust the environment variables to your setup.

Then start it:

```bash
docker compose up
```

## Configuration

All settings are read from environment variables or a `.env` file in the working directory.
Nested settings use `__` as the delimiter (e.g. `FORGE__AUTH_TOKEN`).

| Variable            | Default      | Description                                                                                    |
| ------------------- | ------------ | ---------------------------------------------------------------------------------------------- |
| `CONTENT_DIR`       | _(required)_ | Repo-relative path to the SSG content directory (e.g. `content`)                              |
| `COMMENTS_DIR`      | `comments`   | Subdirectory within `CONTENT_DIR` where comment files are stored                               |
| `REPO_PATH`         | `.`          | Path to the local Git repository                                                               |
| `GIT_PUSH`          | `true`       | `true`: push directly to the default branch; `false`: create a branch and open a merge request |
| `TARGET_BRANCH`     | `main`       | Branch used as base when creating merge requests                                               |
| `LOG_LEVEL`         | `INFO`       | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)                                    |
| `FORGE__TYPE`       | _(required)_ | Forge type — currently only `gitlab`                                                           |
| `FORGE__BASE_URL`   | _(required)_ | Base URL of the GitLab instance                                                                |
| `FORGE__PROJECT_ID` | _(required)_ | Numeric GitLab project ID                                                                      |
| `FORGE__AUTH_TOKEN` | _(required)_ | GitLab personal access token                                                                   |

## API

### `POST /comment`

Accepts a comment submission and stores it as a Markdown file in the repository.

## Motivation

I ran my personal website on WordPress for a long time.
When I considered switching to Hugo, I wanted to preserve the comments my readers had made.
I looked for a service that could accept comment submissions and commit them directly to a static site’s Git repository — but found nothing suitable.

A few years later I discovered [Staticman](https://github.com/eduardoboucas/staticman), which solves exactly this problem and had already existed for years.
Sadly, it is no longer maintained and is written in JavaScript, which kept me from taking over.
Gitmentario is my Python-based answer to the same idea.

## Built with Few Dependencies

- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic & Pydantic Settings](https://pydantic.dev/)
- [python-gitlab](https://python-gitlab.readthedocs.io/)
- [PyYAML](https://pyyaml.org/)

## License

GPLv3
