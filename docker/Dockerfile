# syntax=docker/dockerfile:1
# check=error=true
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HF_HOME=/app/models

WORKDIR /app

# Install dependencies only (layer cached separately from source)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=packages,target=packages \
    uv sync --frozen --no-install-project --no-editable --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Download embedding model into image at build time
RUN python -c \
    "from huggingface_hub import snapshot_download; \
     snapshot_download('hotchpotch/static-embedding-japanese')"

FROM python:3.14-slim-trixie

LABEL maintainer="Kuroki-g"

ENV HF_HOME=/app/models \
    HF_HUB_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    XDG_CACHE_HOME=/app/.cache \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /sbin/nologin appuser && \
    mkdir -p /app/.cache/nidus && \
    chown -R appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/models /app/models
COPY --from=builder --chown=appuser:appuser /app/packages /app/packages

USER appuser

ENTRYPOINT ["nidus"]
CMD ["--help"]
