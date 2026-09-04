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
Copy `compose.yml` and `.env.example` to your setup, rename the latter to `.env` and fill in at least the required values:

```bash
cp .env.example .env
```

Every variable in `.env` overrides the corresponding default baked into `compose.yml`; anything you leave out falls back to that default.

Then start it:

```bash
docker compose up
```

The published port is bound to `127.0.0.1`, so Gitmentario is not reachable from outside the host.
This is deliberate: Gitmentario enforces neither rate limits nor a request body limit itself, so it must run behind a reverse proxy that does — see [Security](#security).
Put your proxy in front of `127.0.0.1:8000`, or, if the proxy runs as a container on the same Docker network, let it reach the `gitmentario` service by name on port 80.

## Configuration

All settings are read from environment variables or a `.env` file in the working directory.
Nested settings use `__` as the delimiter (e.g. `FORGE__AUTH_TOKEN`).

| Variable            | Default      | Description                                                                                    |
| ------------------- | ------------ | ---------------------------------------------------------------------------------------------- |
| `CONTENT_DIR`       | _(required)_ | Repo-relative path to the SSG content directory (e.g. `content`)                               |
| `COMMENTS_DIR`      | `comments`   | Subdirectory within `CONTENT_DIR` where comment files are stored                               |
| `GIT_PUSH`          | `true`       | `true`: push directly to the default branch; `false`: create a branch and open a merge request |
| `TARGET_BRANCH`     | `main`       | Branch used as base when creating merge requests                                               |
| `ALLOWED_ORIGINS`   | _(empty)_    | Comma-separated browser origins allowed to submit comments (e.g. `https://example.com`)        |
| `LOG_LEVEL`         | `INFO`       | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)                                    |
| `FORGE__TYPE`       | _(required)_ | Forge type — currently only `gitlab`                                                           |
| `FORGE__BASE_URL`   | _(required)_ | Base URL of the GitLab instance                                                                |
| `FORGE__PROJECT_ID` | _(required)_ | Numeric GitLab project ID                                                                      |
| `FORGE__AUTH_TOKEN` | _(required)_ | GitLab personal access token                                                                   |

### GitLab Token Permissions

`FORGE__AUTH_TOKEN` may be a personal, group, or project access token.
Gitmentario only ever touches the one project you configured, so a _project access token_ or a _fine-grained token_ restricted to your project is the tightest fit.

#### Fine-grained tokens

[Fine-grained personal access tokens](https://docs.gitlab.com/auth/tokens/fine_grained_access_tokens/) let you grant exactly the actions Gitmentario performs, scoped to a single project:

| Resource        | Action   | Needed for                                             | Endpoint                                         |
| --------------- | -------- | ------------------------------------------------------ | ------------------------------------------------ |
| `Project`       | `Read`   | Looking up the repository's default branch             | `GET /projects/:id`                              |
| `Repository`    | `Read`   | Checking whether a comment file already exists (`409`) | `GET /projects/:id/repository/files/:file_path`  |
| `Repository`    | `Create` | Writing the comment Markdown file                      | `POST /projects/:id/repository/files/:file_path` |
| `Branch`        | `Create` | Only when `GIT_PUSH=false`                             | `POST /projects/:id/repository/branches`         |
| `Merge Request` | `Create` | Only when `GIT_PUSH=false`                             | `POST /projects/:id/merge_requests`              |

With `GIT_PUSH=true` the last two rows can be dropped.

#### Legacy scoped tokens

On older GitLab versions the only scope that covers these endpoints is _`api`_.
`write_repository` is _not_ sufficient:
it grants Git-over-HTTP access, but not the REST Repository Files API that Gitmentario uses.

#### Role

Independently of scopes, the token’s role must allow the write:

- `GIT_PUSH=false` (recommended): _Developer_ is enough – the branch is new and unprotected, and the merge request is reviewed by you.
- `GIT_PUSH=true`: the token commits straight to the default branch. If that branch is protected (default), the role must be one that is allowed to push to it (default: Maintainer).

## Security

Gitmentario accepts writes to your repository from anonymous visitors.
Its defaults are chosen to keep that safe, but a few things are the operator’s responsibility.

### Use a reverse proxy

Gitmentario enforces neither rate limiting nor a request body limit.
That is intentional.
Both belong in the proxy in front of it, which should reject abusive requests before they occupy a worker.
Our example `compose.yml` binds the published port to `127.0.0.1` so the service is not reachable without one.

- Without a rate limit, a script can flood your repository with commits, branches and merge requests.
- Without a body limit, the whole JSON payload is parsed into memory, so a large request is a cheap denial of service.

| Proxy   | Body limit                                          | Rate limit                      |
| ------- | --------------------------------------------------- | ------------------------------- |
| nginx   | `client_max_body_size 64k;` (defaults to `1m`)      | `limit_req_zone` + `limit_req`  |
| Caddy   | `request_body { max_size 64KB }` (no default limit) | `rate_limit` (community module) |
| Traefik | `buffering.maxRequestBodyBytes` (no default limit)  | `rateLimit` middleware          |

### Use Merge Requests

With `GIT_PUSH=true`, every accepted comment is committed directly to your default branch and appears on your live site without review.
Allowing anonymous input to reach your published site without review can turn an ordinary bug into a security problem.
With `GIT_PUSH=false`, a merge request is opened instead, and so a human approves each comment.

### Comments are unauthenticated

There is no known identity behind a comment:
`author` is whatever the submitter typed, so anyone can post under any name, including yours.
The current version of Gitmentario doesn’t support blocklists.

### Rendering is your SSG’s job

The comment body is written to the Markdown file verbatim, and the author name is stored in the YAML frontmatter.
Gitmentario does not attempt to sanitize either, because what is dangerous depends entirely on how your site renders it. For Hugo:

- Keep Goldmark’s `unsafe` setting at `false` (the default). With `unsafe = true`, raw HTML in a comment is rendered as-is, which is stored cross-site scripting on your own domain.
- Do not pass `author` through `safeHTML` in your templates!
- Consider that Markdown alone still allows links and remote images in comments.

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
