ARG PYTHON_VERSION=3.13

### PYTHON BUILDER STAGE
FROM ghcr.io/astral-sh/uv:python$PYTHON_VERSION-trixie-slim AS python-builder

# Configure uv to not download its own Python and to compile bytecode
ENV UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Only copy dependency files first for better layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable

# Copy the application source
COPY ./src ./src

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

### RUNTIME STAGE
FROM python:$PYTHON_VERSION-slim-trixie AS runtime

# Update image
RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m app

# Copy virtualenv and app code from builder stages
COPY --from=python-builder --chown=app:app /app/.venv /app/.venv

USER app

ENV PATH="/app/.venv/bin:$PATH"

# Run the app
CMD ["fastapi", "run", "/app/.venv/lib/python3.13/site-packages/gitmentario/main.py", "--port", "80"]
