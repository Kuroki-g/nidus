# syntax=docker/dockerfile:1
# check=error=true
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HF_HOME=/app/models \
    TRANSFORMERS_OFFLINE=1

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=packages,target=packages \
    uv sync --frozen --no-install-project --no-editable --no-dev

ARG MODEL_MOUNT_PATH
ARG HF_MODEL_DIR="models--hotchpotch--static-embedding-japanese"
ARG MODEL_ID="hotchpotch/static-embedding-japanese"
ARG REVISION="default"
ENV MODEL_SAVE_PATH="${HF_HOME}/hub/${HF_MODEL_DIR}/snapshots/default"

ENV PATH="/app/.venv/bin:$PATH"

RUN --mount=type=bind,source=${MODEL_MOUNT_PATH},target=/tmp/model_source python <<EOF
import os
from sentence_transformers import SentenceTransformer
# Load mounted file and save
model = SentenceTransformer('/tmp/model_source')
save_path = os.path.join(os.environ['HF_HOME'], 'hub', os.environ['HF_MODEL_DIR'], 'snapshots/default')
model.save_pretrained(save_path)
EOF

# Create files to reference
RUN mkdir -p ${HF_HOME}/hub/${HF_MODEL_DIR}/refs/ && \
    echo "default" > ${HF_HOME}/hub/${HF_MODEL_DIR}/refs/main

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.14-slim-trixie

LABEL maintainer="Kuroki-g" \
    version="0.0.1"

ENV HF_HOME=/app/models \
    HF_DATASETS_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser && \
    mkdir -p /app && \
    chown appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/models /app/models
COPY --from=builder --chown=appuser:appuser /app/packages /app/packages

USER appuser

CMD ["python", "packages/mcp-server/src/mcp_server/main.py"]
